try:
    import importlib.resources as ilr
    ilr.files
except AttributeError:
    import importlib_resources as ilr

import logging

import lcm

from lrauv.LCM.Listener import LcmListener
from lrauv.supervisor.Supervisor import Supervisor

from lrauv.supervisor import Logger
logger = None


# TODO change this to use your code
from backseat_app.processing import ProcessingClass


class BackseatApp(Supervisor, LcmListener):

    def __init__(self, lcm_instance, app_cfg):
        Supervisor.__init__(self, lcm_instance, app_cfg)
        LcmListener.__init__(self, lcm_instance)
        global logger
        logger, _ = Logger.configure_logger(name=app_cfg['app_name'])

        self.processing_class = ProcessingClass(lcm_instance, self.cfg)

        # request LCM data from LRAUV
        self.request_slate(self.cfg['lrauv_data'])

        # subscribe LCM handlers
        self.set_timeout(timeout_sec=2.5)
        # TODO change this to add handlers for data requested in config
        self.subscribe(
            {
                self.cfg['lcm_bsd_command_channel']: self.lrauv_command_handler,
                'WetLabsUBAT': self.processing_class.handle_ubat,
                'WetLabsBB2FL': self.processing_class.handle_fluo
            }
        )


    def spin(self):
        """
        Main loop. Handle subscriber callbacks until instructed to shutdown.

        :return: 1 upon exit
        """
        while self.run:
            try:
                # listen to incoming LCM messages with a timeout
                self.listen()
                self.strobe_heartbeat(heart_rate_sec=5.0)
                self.request_data.request()
            except KeyboardInterrupt:
                logger.error("KeyboardInterrupt: aborting.")
                break
        # power down
        self.unsubscribe()
        self.shutdown()
        logger.info("Terminating.")
        exit(1)


def main():
    import argparse
    from lrauv.config.AppConfig import read_config

    default_cfg = ilr.files('backseat_app.config').joinpath('app_config.yml')

    # parse command-line arguments
    parser = argparse.ArgumentParser(description='Runs the LRAUV backseat app.')
    parser.add_argument("-c", "--config", default=default_cfg,
                        type=str, help="set path to app config file")

    args = parser.parse_args()

    # read in app configuration
    cfg = read_config(args.config)

    # init LCM object
    lc = lcm.LCM(cfg['lcm_url'])
    # init BackseatApp
    backseat_app = BackseatApp(lc, cfg)
    # run
    backseat_app.spin()


if __name__ == "__main__":
    main()
