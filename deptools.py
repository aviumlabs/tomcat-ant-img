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

import getopt
import logging
import os
import re
import shutil
import subprocess
import sys

bk_path = os.environ['BACKUP_HOME']
log_file = f'{bk_path}/deptools.log'
logging.basicConfig(format='%(asctime)s %(message)s', filename=log_file, encoding='utf-8', level=logging.INFO)
logger = logging.getLogger(__name__)


def main(argv):
    os.environ['SPTARGET'] = os.environ['INSTANCE_NAME']
    
    # main program
    help_text = """deptools.py [-h|--help] [-s|--init-iiq] [-b|--backup-db SCHEMA] 
                               [-d|--deploy-iiq]
    Options:
    -h, --help              Show this help message and exit
    -s, --init-iiq          Initialize IIQ environment
    -b, --backup-db SCHEMA  Backup the specified database schema
    -d, --deploy-iiq        Build and deploy IIQ WAR file to Tomcat webapps directory
    """

    try:
        opts, args = getopt.getopt(argv, "hsb:d", ["help", "init-iiq", "backup-db=", "deploy-iiq"])

        for opt, arg in opts:
            if opt in ('-h', '--help'):
                print(help_text)
                sys.exit()
            elif opt in ('-s', '--init-iiq'):
                initialize_iiq_env()
                sys.exit()
            elif opt in ('-b', '--backup-db'):
                backup_db(arg)
                sys.exit()
            elif opt in ('-d', '--deploy-iiq'):
                deploy_iiq()
                sys.exit()
            else:
                print(help_text)
                sys.exit()

    except getopt.GetoptError:
        print(help_text)
        sys.exit(2)


def backup_db(schema: str):
    logger.info("Backup database...")
    backup_path = os.environ['BACKUP_HOME']

    pg_url = get_postgresql_url(schema)

    pg_out = subprocess.Popen(['pg_dump',
                               pg_url,
                               '-F',
                               'c',
                               '-f',
                               os.path.join(backup_path, f'{schema}_backup.dump')],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    
    stdout, stderr = pg_out.communicate()

    if stderr:
        logger.error("Error during database backup...")
        logger.error(stderr.decode())
    else:
        logger.info(stdout.decode())


def build_iiq():
    logger.info("Building IIQ...")
    ssb_home = os.environ['SSB_HOME']
    build_script = os.path.join(ssb_home, 'build.sh')

    if os.path.exists(os.path.join(ssb_home, 'build', 'extract')):
        # Run build clean
        bd_out = subprocess.Popen([build_script, "clean"],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)

        stdout, stderr = bd_out.communicate()

        if stderr:
            logger.error("Error during build clean... ")
            logger.error(stderr.decode())
        else:
            logger.info(stdout.decode())

    # Run build
    bd_out = subprocess.Popen([build_script, "war"],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    
    stdout, stderr = bd_out.communicate()

    if stderr:
        logger.error("Error during build...")
        logger.error(stderr.decode())
    else:
        logger.info(stdout.decode())

    iiq_war_path = os.path.join(ssb_home, 'build', 'deploy', 'identityiq.war')

    deploy_path = os.path.join(os.environ['CATALINA_BASE'], 'webapps')

    if os.path.exists(iiq_war_path):
        if os.path.exists(deploy_path):
            shutil.copy(iiq_war_path, deploy_path)
        else:
            raise FileNotFoundError("Tomcat webapps deployment path not found.")
    else:
        raise FileNotFoundError("IIQ WAR file not found.")    



def copy_update_iiq_properties(db_hostname: str = 'db'):
    logger.info("Copying IIQ property files...")

    ssb_home = os.environ['SSB_HOME']
    # Copy sandbox.iiq.properties to <instance_name>.iiq.properties
    inst_name = os.environ['INSTANCE_NAME']
    src_iiq = os.path.join(ssb_home, 'sandbox.iiq.properties')
    dest_iiq = os.path.join(ssb_home, inst_name + '.iiq.properties')

    if not os.path.exists(dest_iiq):
        shutil.copyfile(src_iiq, dest_iiq)
        update_iiq_properties(dest_iiq, db_hostname)

    # Copy sandbox.log4j2.properties to <instance_name>.log4j2.properties
    src_log4j2 = os.path.join(ssb_home, 'sandbox.log4j2.properties')
    dest_log4j2 = os.path.join(ssb_home, inst_name + '.log4j2.properties')

    if not os.path.exists(dest_log4j2):
        shutil.copyfile(src_log4j2, dest_log4j2)
        update_log4j2_properties(dest_log4j2)


def create_schema(schema: str):
    pg_url = get_postgresql_url()

    # Create the parent schema if it does not exist
    create_schema_sql = f"CREATE SCHEMA IF NOT EXISTS {schema};"

    psql_command = [
        'psql',
        pg_url,
        '-c',
        create_schema_sql
    ]

    psql_out = subprocess.Popen(psql_command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
    
    stdout, stderr = psql_out.communicate()

    if stderr:
        logger.error("Error during schema creation...")
        logger.error(stderr.decode())
    else:
        logger.info(stdout.decode())


def deploy_iiq():
    logger.info("Deploying IIQ...")
    build_iiq()


def extract_iiq():
    ssb_home = os.environ['SSB_HOME']
    build_script = os.path.join(ssb_home, 'build.sh')
    extract_path = os.path.join(ssb_home, 'build', 'extract')

    # Run build clean
    if os.path.exists(extract_path):
        bd_out = subprocess.Popen([build_script, "clean"],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)

        stdout, stderr = bd_out.communicate()

        if stderr:
            logger.error("Error during build clean... ")
            logger.error(stderr.decode())
        else:
            logger.info(stdout.decode())

    # Run build
    bd_out = subprocess.Popen([build_script],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    
    stdout, stderr = bd_out.communicate()

    if stderr:
        logger.error("Error during build...")
        logger.error(stderr.decode())
    else:
        logger.info(stdout.decode())


def get_postgresql_url(schema :str = 'postgres') -> str:
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
            pg_url = f'postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{schema}'
            return pg_url
        else:
            raise ValueError("PostgreSQL password file is empty.")
    else:
        raise FileNotFoundError("PostgreSQL password file not found.")
    

def get_tomcat_mgr_url() -> str:
    tls_port = os.environ['TC_SECURE_PORT']
    tomcat_host = os.uname().nodename
    if not tls_port:
        tls_port = '8443'

    tomcat_url = f'https://{tomcat_host}:{tls_port}/manager/text/'

    return tomcat_url


def get_tomcat_mgr_credentials() -> str:
    rpauser_pass_path = os.environ['SECRETS_HOME'] + '/rpauser.pass'
    if os.path.exists(rpauser_pass_path):
        with open(rpauser_pass_path, 'r') as f:
            rpauser_pass = f.read().strip()

        if rpauser_pass:
            return rpauser_pass
        else:
            raise ValueError("RPA user password file is empty.")
    else:
        raise FileNotFoundError("RPA user password file not found.")
    

def initialize_iiq_env():
    logger.info("Initializing IIQ environment...")
    
    extract_path = os.path.join(os.environ['SSB_HOME'], 'build', 'extract', 'WEB-INF', 'database') 
    iiq_tables_path = os.path.join(extract_path, 'create_identity_tables-8.4.postgresql')
    iiq_tables_update_path = os.path.join(extract_path, 'upgrade_identity_tables-8.4*.postgresql')

    schema = os.environ['INSTANCE_NAME']
    create_schema(schema)
    copy_update_iiq_properties()
    extract_iiq()
    install_db_schema(iiq_tables_path, schema)
    install_db_schema(iiq_tables_update_path, schema)
    

def install_db_schema(sql_file: str, schema: str):
    pg_url = get_postgresql_url(schema)
    
    if os.path.exists(sql_file):
        logger.info(f"Loading schema file... {sql_file}")
        load_sql_file(pg_url, sql_file)
    else:
        logger.error("Schema file not found.")
        raise FileNotFoundError(f"IIQ schema SQL file not found: {sql_file}")
        
    

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
        logger.info(stdout.decode())


def update_iiq_properties(prop_file_path: str, db_hostname: str = 'db'):
    logger.info("Updating IIQ properties...")
    ssb_home = os.environ['SSB_HOME']
    iiq_properties_path = os.path.join(ssb_home, prop_file_path)

    # Update the iiQ properties database connection settings
    match_term = r'devsrv(:5432)'
    replace_term = f'{db_hostname}\\2'

    with open(iiq_properties_path, 'r') as f:
        iiq_properties = f.read()

    iiq_properties = re.sub(match_term, replace_term, iiq_properties)

    with open(iiq_properties_path, 'w') as f:
        f.write(iiq_properties)


def update_log4j2_properties(log4j2_prop_path: str):
    logger.info("Updating log4j2 properties...")
    ssb_home = os.environ['SSB_HOME']
    log4j2_properties_path = os.path.join(ssb_home, log4j2_prop_path)

    # Update the log4j2 properties to write logs to the instance logs directory
    match_term = r'env:TC_INSTANCE'
    replace_term = r'INSTANCE_NAME'

    with open(log4j2_properties_path, 'r') as f:
        log4j2_properties = f.read()

    log4j2_properties = re.sub(match_term, replace_term, log4j2_properties)

    with open(log4j2_properties_path, 'w') as f:
        f.write(log4j2_properties)


if __name__ == '__main__':
    main(sys.argv[1:])