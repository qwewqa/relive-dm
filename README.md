# relive-dm
Datamining utilities for Revue Starlight Re LIVE


## Development Setup

### Prerequisites
1. Windows or Linux (MacOS is not supported)
2. Python 3.10 or later
3. pdm (Dependency manager), see https://pdm-project.org/latest/
4. If on Linux, ensure libasound2 is installed

### Installation
1. Clone this repository
2. Run `pdm install` to install dependencies (you may need to delete `pdm.lock` in case of errors)
3. Activate the virtual environment, see https://pdm-project.org/dev/usage/venv/
4. Run `relive-dm download --path <output_path>` to download the game data (may take several hours from scratch, requires 40-50GB of disk space)
