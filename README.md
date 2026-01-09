# LRAUV Backseat Python Application Example

Python package that serves as an example and
[template repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template)
for your own LRAUV backseat application which uses the LRAUV Backseat LCM Interface python library
[here](https://bitbucket.org/mbari/lrauv-backseat-helper).

## Quick Start

First go to the above link and install the LRAUV Backseat LCM Interface library! It is a dependency for any LRAUV backseat Python app.

## Python Version Compatibility

This package was originally developed for Python 3.8. The build and install scripts use `python3.8` by default.

### Using Python 3.11+ (including 3.12)

If you're using Python 3.11 or newer, you'll need to make some modifications to the scripts:

#### 1. Configure Shell Environment

Add user-installed executables to PATH:
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

#### 2. Modify build.sh

In `build.sh`, change line 4: `python3.8 -m build` → `python3 -m build`

#### 3. Modify install.sh

In `install.sh`, change python3.8 to python3. You may also need the --break-system-packages flag for Python3.11+ due to PEP 668 compliance.

## Quick Start Installation

Complete setup from scratch:

```bash
# 1. Install lrauv-backseat-helper library (required dependency)
# See: https://bitbucket.org/mbari/lrauv-backseat-helper
cd ~/path/to/lrauv-backseat-helper
./build.sh && ./install.sh

# 2. Get the template
# Option A: Use GitHub's "Use this template" button to create your own repository, then:
#   git clone <your-repo-url>
#   cd <your-repo-name>
# Option B: Clone the template directly (this is going to be weird and less correct!):
git clone https://github.com/mbari-org/lrauv_backseat_python_template.git
cd lrauv_backseat_python_template

# 3. Build and install (for Python 3.8)
./build.sh   # Builds wheel
./install.sh # Installs backseat_app

# 4. Run the app
backseat_app
```

**For Python 3.11+:** See the "Python Version Compatibility" section above for required script modifications.

The template repository is ready to run immediately. It will:
- Listen for backseat commands from the vehicle
- Publish a heartbeat every 5 seconds
- Handle shutdown commands

This provides a minimal working backseat application that you can extend with your own data processing.

To run the app after installation:
```bash
$ backseat_app
```

**Note:** Ensure `$HOME/.local/bin` is in your PATH (see "Python Version Compatibility" section above).

## Install App Package

Scripts have been included for conveniently installing the python app package.

### Build

Build a wheel with:
```bash
$ ./build.sh
```

### Install

Install the wheel with:
```bash
$ ./install.sh
```

### Cleanup

Remove build files with:
```bash
$ ./cleanup.sh
```

### Do All Three

Perform cleanup/build/install:
```bash
$ ./cycle.sh
```

## Adding Custom Data Processing

The `backseat_app/main.py` file is provided as a working sample. You can:
- Use it as-is and add a processing class to handle specific data
- Use it as an example and modify it for your needs

To add custom data processing to handle specific LCM messages:

1. Create a processing module (e.g., `backseat_app/processing.py`) with handler methods
2. Import your processing class at the top of `backseat_app/main.py`
3. Instantiate your processing class in `BackseatApp.__init__()`
4. Add your handlers to the `subscribe()` dict

See the comments in `backseat_app/main.py` and the example below.

## Package Structure

This template repository implements the following structure:

```
backseat_app_package
|__ pyproject.toml
|__ setup.cfg
|__ + backseat_app
    |__ __init__.py
    |__ main.py
    |__ processing.py (you create this for custom processing)
    |__ + config
        |__ __init__.py
        |__ app_cfg.yaml
```

### Example Custom Processing Implementation

Here's a simple example of a processing module that handles sensor data:

```python
# backseat_app/processing.py
import logging
from lrauv.LCM.HandlerBase import LcmHandlerBase
from lrauv.LCM.Publisher import LcmPublisher

logger = logging.getLogger('backseat_app')

class SensorProcessor(LcmHandlerBase):
    def __init__(self, lcm_instance, cfg):
        super().__init__(lcm_instance, cfg)
        self.publisher = LcmPublisher(lcm_instance)
        self.chlorophyll_threshold = 2.5
    
    def handle_fluo(self, channel, data):
        """Process chlorophyll fluorescence data from WetLabsBB2FL sensor"""
        logger.debug(f"Handling LCM msg on channel {channel}")
        msg = self.decode(data)
        
        if 'mass_concentration_of_chlorophyll_in_sea_water' not in self.get_item_names(msg):
            return
        
        chl_var = self.get_variable('mass_concentration_of_chlorophyll_in_sea_water', msg)
        if not chl_var or len(chl_var.data) == 0:
            logger.warning("No chlorophyll data in message")
            return
        
        chl_value = chl_var.data[0]
        logger.info(f"Chlorophyll reading: {chl_value:.2f} ug/L")
        
        if chl_value > self.chlorophyll_threshold:
            logger.warning(f"High chlorophyll detected: {chl_value:.2f} ug/L")
            self.publish_alert(msg.epochMillisec, chl_value)
    
    def publish_alert(self, timestamp, value):
        """Publish a detection alert to the vehicle's slate"""
        self.publisher.clear_msg()
        self.publisher.timestamp(timestamp)
        self.publisher.add_variable(
            name='_.high_chlorophyll_detected',
            val=value,
            unit='ug/L'
        )
        self.publisher.publish('tethys_slate')
        logger.info("Published chlorophyll alert")
```

Then update `backseat_app/main.py`:

```python
# Import your processing class
from backseat_app.processing import SensorProcessor

class BackseatApp(Supervisor, LcmListener):
    def __init__(self, lcm_instance, app_cfg):
        # ... initialization code ...
        
        # Instantiate your processor
        self.sensor_processor = SensorProcessor(lcm_instance, self.cfg)
        
        # Subscribe to channels with your handlers
        self.subscribe(
            {
                self.cfg['lcm_bsd_command_channel']: self.lrauv_command_handler,
                'WetLabsBB2FL': self.sensor_processor.handle_fluo,
            }
        )
```

### Config

You must also add a config module in your app as described in the example app structure above. It must
contain a modified yaml file like the one in `backseat_app/config/app_cfg.yaml`

## Install Your App As A Service

The LRAUV Backseat Helper package includes a utility script to install your backseat app as a Linux systemd service.

### Prerequisites

1. **Install the LRAUV Backseat Helper package first** (if you haven't already):
   ```bash
   # For Python 3.8
   $ pip install lrauv-backseat-helper

   # For Python 3.11+
   $ pip install --break-system-packages lrauv-backseat-helper
   ```

2. **Build and install your backseat app package**:
   ```bash
   $ ./cycle.sh  # or ./build.sh && ./install.sh
   ```

3. **Service installation prerequisites:**
   ```bash
   # Create the /LRAUV directory
   sudo mkdir -p /LRAUV
   sudo chown $USER:$USER /LRAUV

   # Create empy symlink (Python 3.11+ only - the empy package installs as em.py)
   ln -s ~/.local/bin/em.py ~/.local/bin/empy

   # Ensure PATH is configured (see "Python Version Compatibility" section above)
   ```

### Creating the Service

Use the `lrauv_install_service` script to create a systemd service for your app.

**Parameters:**
- `app_name`: Name for your service (e.g., "backseat_app")
- `app_directory`: Full path to your app's source directory
- `console_script_name`: Name of the console script installed by your package (found in `~/.local/bin/`)

**For Python 3.8:**
```bash
$ lrauv_install_service backseat_app ~/lrauv_backseat_python_template backseat_app
```

**For Python 3.11+**, you may need to preserve the environment when running with sudo. Replace `python3.12` with your Python version (e.g., `python3.11`, `python3.12`):
```bash
$ sudo env PATH="$PATH" PYTHONPATH="$HOME/.local/lib/python3.12/site-packages:$PYTHONPATH" \
    $HOME/.local/bin/lrauv_install_service backseat_app ~/lrauv_backseat_python_template backseat_app
```

**What this does:**
- Creates a systemd service file at `/etc/systemd/system/backseat_app.service`
- Creates a symlink from your app directory to `/LRAUV/backseat_app`
- Creates a start script at `/LRAUV/backseat_app/start_backseat_app` that:
  - Automatically detects the primary network interface
  - Adds multicast route for LCM (224.0.0.0/4)
  - Starts the application in a screen session
- Enables and starts the service
- Logs will be written to `/LRAUV/backseat_app/logs/` and `/LRAUV/backseat_app/bs.log`

**Note:** The start script uses `sudo` to add the multicast route. Ensure the user has sudo privileges or configure passwordless sudo for the route command.

**Optional: Configure passwordless sudo for route command**

To allow the service to add multicast routes without a password prompt, add this to sudoers:
```bash
# Run this command to edit sudoers safely:
sudo visudo

# Add this line (replace 'tethysadmin' with your username):
tethysadmin ALL=(ALL) NOPASSWD: /sbin/route
```

### Managing the Service

Once installed, you can manage your service using systemctl:

#### Stop
```bash
$ sudo systemctl stop your_app.service
```

#### Restart
```bash
$ sudo systemctl restart your_app.service
```

#### Disable

This will disable your app from running automatically when the backseat boots up.

```bash
$ sudo systemctl status your_app.service
```

#### Enable

This will enable your app to automatically run when the backseat boots up.

```bash
$ sudo systemctl status your_app.service
```
