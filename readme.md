# Tableau Project Data

Get Project data from Tableau Server using the Tableau Server Client (TSC) library and VizPortal APIs

## Requirements

- Python 3.6+
- Tableau Server Client (TSC) library

## Installation

1. Clone this repository
2. Navigate to the directory where you cloned the repository
3. Create a virtual environment
4. Activate the virtual environment
5. Install the requirements

```bash
git clone
cd tableau-project-data
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
usage: main.py [-h] [--server SERVER] [--site SITE] [--token-name TOKEN_NAME] [--token-value TOKEN_VALUE] 

optional arguments:
  -h, --help 
      show this help message and exit
  --token-name TOKEN_NAME, -N TOKEN_NAME 
      name of the personal access token used to sign into the server
  --token-value TOKEN_VALUE, -v TOKEN_VALUE
      value of the personal access token used to sign into the server
  --server SERVER, -s SERVER 
      server url address
  --site SITE, -T SITE
      site name
```


