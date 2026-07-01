#!/usr/bin/env python
# deptools.py
# Copyright 2024, 2025, 2026 Michael Konrad 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import configparser
import getopt
import logging
import os
import re
import requests
import subprocess
import sys
import time

from pathlib import Path


bk_path = os.environ['BACKUP_HOME']
log_file = os.path.join(bk_path, 'deptools.log')

logging.basicConfig(format='%(asctime)s %(message)s', filename=log_file, encoding='utf-8', level=logging.INFO)
logger = logging.getLogger(__name__)

def main(argv):
    # main program
    help_text = """deptools.py [-h|--help] [-b|--backup-db DATABASE] 
                               [-d|--deploy-war FILE] [-s|--start-app]
    Options:
    -h, --help                Show this help message and exit
    -b, --backup-db DATABASE  Backup the specified database schema
    -d, --deploy-war FILE     Deploy a web application archive, specify the full path 
                              of the web archive file. The application context is 
                              automatically determined from the wab archive file name.
    -s, --start-app APP       Start a deployed web application, provide the name of the 
                              web application to start.
    """

    try:
        opts, args = getopt.getopt(argv, "hb:d:s:", ["help", "backup-db=", "deploy-war=", 
                                                     "start-app="])

        for opt, arg in opts:
            if opt in ('-h', '--help'):
                print(help_text)
                sys.exit()
            elif opt in ('-b', '--backup-db'):
                backup_db(arg)
                sys.exit()
            elif opt in ('-d', '--deploy-war'):
                deploy_war(arg)
                sys.exit()
            elif opt in ('-s', '--start-app'):
                start_app(arg)
                sys.exit()
            else:
                print(help_text)
                sys.exit()

    except getopt.GetoptError:
        print(help_text)
        sys.exit(2)


def deploy_war(war_file_path: str):
    logger.info("Preparing deployment...")
    print("Preparing deployment...")

    if war_file_path and os.path.exists(war_file_path):
        war_name = os.path.basename(war_file_path)
        app_context = os.path.splitext(war_name)[0]
            
        tomcat_url = get_tomcat_mgr_url()
        tomcat_user, tomcat_pass = get_tomcat_rpa_credentials()
        deploy_url = f"{tomcat_url}deploy?path=/{app_context}&update=true"
        with open(war_file_path, 'rb') as war_file:
            response = requests.put(deploy_url, auth=(tomcat_user, tomcat_pass), data=war_file, verify=False)
        if response.status_code == 200:
            logger.info(f"{app_context} deployed successfully.")
            print(f"{app_context} deployed successfully.")
        else:
            logger.error(f"Failed to deploy {app_context}. HTTP status code: {response.status_code}")
            print(f"Failed to deploy {app_context}. HTTP status code: {response.status_code}")
            sys.exit(1)
    else:
        logger.error(f"Web application archive {war_file_path} not found.")
        print(f"Web application archive {war_file_path} not found.")


def reload_app(app: str):
    if app:
        if check_valid_characters(app):
            logger.info(f"Reloading application {app}...")
            print(f"Reloading application {app}...")
            tomcat_url = get_tomcat_mgr_url()
            tomcat_user, tomcat_pass = get_tomcat_rpa_credentials()
            start_url = f"{tomcat_url}reload?path=/{app}"
            response = requests.put(start_url, auth=(tomcat_user, tomcat_pass), data=app, verify=False)
            if 200 == response.status_code:
                logger.info(f"Reload response..{response.text}")
                print(f"Reload response..{response.text}")
            else:
                logger.error(f"Failed to reload {app}. HTTP status code..{response.status_code}.")
                print(f"Failed to reload {app}. HTTP status code..{response.status_code}.")
                logger.error(f"Reload response..{response.text}")
                print(f"Reload response..{response.text}.")       


def start_app(app: str):
    if app:
        if check_valid_characters(app):
            logger.info(f"Starting application {app}...")
            print(f"Staring application {app}...")

            tomcat_url = get_tomcat_mgr_url()
            tomcat_user, tomcat_pass = get_tomcat_rpa_credentials()
            start_url = f"{tomcat_url}start?path=/{app}"
            response = requests.put(start_url, auth=(tomcat_user, tomcat_pass), data=app, verify=False)
            if 200 == response.status_code:
                logger.info(f"Start response..{response.text}.")
                print(f"Start response..{response.text}.")
                logger.info(f"{app} started successfully.")
                print(f"{app} started successfully.")
            else:
                logger.error(f"Failed to start {app}. HTTP status code..{response.status_code}")
                logger.error(f"Start response...{response.text}.")
                print(f"Failed to start {app}. HTTP status code..{response.status_code}")
                print(f"Start response..{response.text}.")
                sys.exit(1)
        else:
            logger.error("Application name provided is invalid.")
            print("Application name provided is invalid.")


def stop_app(app: str):
    if app:
        if check_valid_characters(app):
            logger.info(f"Stopping application {app}...")
            print(f"Stopping application {app}...")

            tomcat_url = get_tomcat_mgr_url()
            tomcat_user, tomcat_pass = get_tomcat_rpa_credentials()
            start_url = f"{tomcat_url}stop?path=/{app}"
            response = requests.put(start_url, auth=(tomcat_user, tomcat_pass), data=app, verify=False)
            if 200 == response.status_code:
                logger.info(f"Stop response...{response.text}.")
                print(f"Stop response...{response.text}.")
                logger.info(f"{app} stopped successfully.")
                print(f"{app} stopped successfully.")
            else:
                logger.error(f"Failed to stop {app}. HTTP status code..{response.status_code}")
                logger.error(f"Stop response...{response.text}.")
                print(f"Failed to stop {app}. HTTP status code..{response.status_code}")
                print(f"Stop response...{response.text}.")
                sys.exit(1)
        else:
            logger.error("Application name provided is invalid.")
            print("Application name provided is invalid.")


def backup_db(database: str):
    backup_path = os.environ['BACKUP_HOME']

    if database:
        if check_valid_characters(database):
            logger.info("Backup database...")
            pg_url = get_postgresql_url(database)

            pg_out = subprocess.Popen(['pg_dump',
                                    pg_url,
                                    '-F',
                                    'c',
                                    '-f',
                                    os.path.join(backup_path, f'{database}_backup.dump')],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
            
            stdout, stderr = pg_out.communicate()

            if stderr:
                logger.error("Error during database backup...")
                logger.error(stderr.decode())
            else:
                logger.info(stdout.decode())
        else:
            logger.error("Provided database is invalid.")
            print(("Provided database is invalid."))


def create_database(database: str):
    if database:
        if check_valid_characters(database):
            pg_url = get_postgresql_url(database)

            # Create the parent database if it does not exist
            create_database_sql = f'"CREATE DATABASE {database};"'

            psql_command = [
                'psql',
                pg_url,
                '-c',
                create_database_sql
            ]

            psql_out = subprocess.Popen(psql_command,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT)
            
            stdout, stderr = psql_out.communicate()

            if stderr:
                logger.error("Error during database creation...")
                logger.error(stderr.decode())
            else:
                logger.info(stdout.decode())
        else:
            logger.error("Provided database is invalid.")
            print("Provided database is invalid.")
    else:
        logger.error("Please specify the database to create.")
        print("Please specify the database to create.")


def check_valid_characters(value: str):
    if not re.match("^[a-z]*$", value):
        return False
    # Only alpha characters allowed
    return True

def get_postgresql_url(database: str = 'postgres') -> str:
    # Construct the PostgreSQL connection URL
    if 'PG_HOST' in os.environ:
        pg_host = os.environ["PG_HOST"]
    else:
        pg_host = os.uname().nodename

    if 'PG_PORT' in os.environ:
        pg_port = os.environ["PG_PORT"]
    else:
        pg_port = '5432'

    if 'PG_USER' in os.environ:
        pg_user = os.environ["PG_USER"]
    else:
        pg_user = 'postgres'

    pg_pass_path = os.environ['POSTGRES_PASSWORD_FILE']

    if os.path.exists(pg_pass_path):
        with open(pg_pass_path, 'r') as f:
            pg_pass = f.read().strip()

        if pg_pass:
            pg_url = f'postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{database}'
            return pg_url
        else:
            raise ValueError("PostgreSQL password file is empty.")
    else:
        raise FileNotFoundError("PostgreSQL password file not found.")
    

def get_tomcat_mgr_url() -> str:
    tls_port = os.environ['TC_SECURE_PORT']
    if not tls_port:
        tls_port = '8443'
    # Tomcat Manager text interface
    tomcat_url = f'https://localhost:{tls_port}/manager/text/'
    return tomcat_url


def get_tomcat_rpa_credentials():
    tomcat_config, keystore_config = parse_config()
    rpa_user = tomcat_config['rpauser']
    rpa_pass_file = tomcat_config['rpapass']
    rpauser_pass_path = os.path.join(os.environ['SECRETS_HOME'], rpa_pass_file)
    if os.path.exists(rpauser_pass_path):
        with open(rpauser_pass_path, 'r') as f:
            rpauser_pass = f.read().strip()
        if rpauser_pass and rpa_user:
            return rpa_user, rpauser_pass
        else:
            raise ValueError("RPA user password file is empty.")
    else:
        raise FileNotFoundError("RPA user password file not found.")


def install_db_schema(sql_file: str, database: str = 'postgres'):
    pg_url = get_postgresql_url(database)
    
    if os.path.exists(sql_file):
        logger.info(f"Loading schema file... {sql_file}")
        print(f"Loading schema file... {sql_file}")
        load_sql_file(pg_url, sql_file)
    else:
        logger.error(f"Schema file not found...{sql_file}")
        print(f"Schema file not found... {sql_file}")
        raise FileNotFoundError(f"SQL file not found.")
    

def is_app_running(app: str) -> bool:
    # curl -u username:password http://localhost:8080/manager/text/list
    if app:
        if check_valid_characters(app):
            tomcat_url = get_tomcat_mgr_url()
            tomcat_user, tomcat_pass = get_tomcat_rpa_credentials()
            start_url = f"{tomcat_url}list"
            response = requests.get(start_url, auth=(tomcat_user, tomcat_pass), data=app, verify=False)
            if 200 == response.status_code:
                results = response.text.splitlines()
                match_term = f"/{app}:running"
                for line in results:
                    if re.match(match_term, line):
                        app_status = True
            else:
                app_status = False
            return app_status
        else:
            logger.error("Invalid application name provided.")
            return False
    else:
        logger.error("Application name is required.")
        return False


def load_sql_file(pg_url, sql_file_path):
    # Load the SQL file into the PostgreSQL database using psql
    psql_command = [
        'psql',
        pg_url,
        '-f',
        sql_file_path
    ]

    psql_out = subprocess.Popen(psql_command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)

    stdout, stderr = psql_out.communicate()

    if stderr:
        logger.error("Error during SQL file load...")
        logger.error(stderr.decode())
    else:
        logger.info("SQL file load completed.")
        logger.info(stdout.decode())


def parse_config():
    conf_file = os.path.join(os.environ['SECRETS_HOME'], 'tomcat.config')
    parser = configparser.ConfigParser()
    parser.read(conf_file)
    # Tomcat configuration dictionary
    tomcat_config = {}
    if 'tomcat' in parser:
        tomcat_config = dict(parser['tomcat'])
    # Keystore configuration dictionary
    keystore_config = {}
    if 'keystore' in parser:
        keystore_config = dict(parser['keystore'])
    # return configuration dictionaries
    return tomcat_config, keystore_config


if __name__ == '__main__':
    main(sys.argv[1:])