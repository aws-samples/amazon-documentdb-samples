## Requirement:

A suitable Elastic Compute Cloud or EC2 environment with sufficient CPU and RAM with Python version 3.8.

1. Setup on Amazon EC2:

Update the setup_lab.sh script by adding your environment specific endpoints, username, password, and other environment specific parameters.
You can find the values in your AWS console by navigating to the service.

Source the file so that the configuration values are exported to the current shell.

	source setup_lab.sh

Create a lab directory

	mkdir better-together

2. Copy the necessary files to your lab.

Copy the 4 files from the repo or clone the entire repo.
Make sure you have the following files and directories in your lab environment's home directory:

load_test/
logs/
plot_better_together_results.ipynb
README
requirements.txt

Under load_test direcotry you need the following two Python scripts:

ls -1 load_test/
scenario01_docdb_test.py
scenario02_docdb_test.py

3.  Python virtual environment

Create a virtual environment in your lab directory

	python3 -m venv $PWD/.venv

Activate it and verify the version:

	$ source .venv/bin/activate
    $ python -V
	$ Python 3.8.16

Install required packages:

	pip install -r requirements.txt

4.  Execution

There are two scenarios: scenario01 using AWS DocumentDB only and 2 DocumentDB paired with AWS ElastiCache

Sample Execution:
Both scripts take the same parameters.
1 The number of threads
2 The number of executions per thread
3 Logfile identifier

All parameters are optional and they default to the following values:

number of threads 25
number of execution 10000
logfile identifier a random generated string

For example, one thread executing 10 queries, and random generated log identifier:

	python load_test/scenario02_docdb_test.py 1 10
	Connected to DocumentDB and found a random document
	Connected to ElastiCache
	Cache hits: 10
	Cache misses: 0
	Logfile located here: logs/1/scenario02_DOCDB_9929_37zczgu8.json

5.  Analyze and visualize results via the included Jupyter notebook.

To start Jupyter lab in your virtual envirnment execute:

  	jupyter lab --ip 0.0.0.0

From your AWS console or similar open a browser to the EC2's public IP address. Change the URL from https to http and the port to 8888.
Make sure that you have opened ingress rules only for your computer IP address on port 8888.

example URL:

    <http://1.2.3.4:8888/>

Once Jupyter starts up it will display the access as one of the last messages.

	<http://127.0.0.1:8888/lab?token=58b4cbaa7202f3bf8757310d9b2b8548555b508c815479b1>

Copy the string after the equal sign and paste it into the newly opened tab on your browser. The notebook will load.

Once the notebook is loaded select the file plot_better_together_results.ipynb if not already selected.
Update the value of the scenario variable with the logfile name displayed after the execution.

For example:

    scenario = 'scenario02_DOCDB_929_37zczgu8.json'

Then select Run->Run All Cells

Note: ElastiCache is designed for ultra-high speed.
Small execution sets are not going to generate meaningful results that is why the default values are set to 25 threads and 10000 execution per thread.
We suggest to start with a smaller workload and gradually increase it. Perhaps start with 2 threads and 5000 executions.


