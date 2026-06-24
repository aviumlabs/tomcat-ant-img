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
import time

from pathlib import Path


bk_path = os.environ['BACKUP_HOME']
log_file = f'{bk_path}/deptools.log'
logging.basicConfig(format='%(asctime)s %(message)s', filename=log_file, encoding='utf-8', level=logging.INFO)
logger = logging.getLogger(__name__)


def main(argv):
    os.environ['SPTARGET'] = os.environ['INSTANCE_NAME']
    
    # main program
    help_text = """deptools.py [-h|--help] [-s|--setup-iiq] [-b|--backup-db SCHEMA] 
                               [-d|--deploy-iiq EXTEND]
    Options:
    -h, --help              Show this help message and exit
    -s, --setup-iiq         Initial setup of the IdentityIQ environment 
    -b, --backup-db SCHEMA  Backup the specified database schema
    -d, --deploy-iiq EXTEND Build and deploy IdentityIQ, pass y if extended schema 
                            should be installed.
    """

    try:
        opts, args = getopt.getopt(argv, "hsb:d:", ["help", "setup-iiq", "backup-db=", "deploy-iiq="])

        for opt, arg in opts:
            if opt in ('-h', '--help'):
                print(help_text)
                sys.exit()
            elif opt in ('-s', '--setup-iiq'):
                setup_iiq()
                sys.exit()
            elif opt in ('-b', '--backup-db'):
                backup_db(arg)
                sys.exit()
            elif opt in ('-d', '--deploy-iiq'):
                if not arg:
                    deploy_iiq()
                elif arg.lower() == 'y':
                    deploy_iiq(extend_schema=True)
                elif arg.lower() == 'n':
                    deploy_iiq()
                else:
                    print(help_text)
                    sys.exit()

                sys.exit()
            else:
                print(help_text)
                sys.exit()

    except getopt.GetoptError:
        print(help_text)
        sys.exit(2)


def setup_iiq():
    """
    This build specifically supports PostgreSQL.
    Initialize the IdentityIQ environment by extracting the build,
    copying and updating properties files, and installing the databases.
    """

    logger.info("Initializing IdentityIQ environment...")
    print("Initializing IdentityIQ environment...")

    build_iiq(war=False)

    copy_update_iiq_properties()

    extract_path = os.path.join(os.environ['SSB_HOME'], 'build', 'extract', 'WEB-INF', 'database')
    if not os.path.exists(extract_path):
        raise FileNotFoundError("IIQ database schema extract path not found. Please run the build to extract the database schema.")
    else:
        iiq_tables_path = os.path.join(extract_path,'create_identityiq_tables-8.4.postgresql')
        up_file = list(Path(extract_path).glob('upgrade_identityiq_tables-8.4*.postgresql'))
        iiq_tables_update_path = str(up_file[0])
    
        logger.info("Installing IdentityIQ databases...")
        print("Installing IdentityIQ databases...")
        install_db_schema(iiq_tables_path)
        install_db_schema(iiq_tables_update_path)
        logger.info("IdentityIQ environment initialization complete.")
        print("IdentityIQ environment initialization complete.")


def deploy_iiq(extend_schema: bool = False):
    ssb_home = os.environ['SSB_HOME']
    logger.info("Preparing deployment...")
    print("Preparing deployment...")
    build_iiq(war=True)

    # Deploy the war
    iiq_war_path = os.path.join(ssb_home, 'build', 'deploy', 'identityiq.war')

    deploy_path = os.path.join(os.environ['CATALINA_BASE'], 'webapps')

    if os.path.exists(iiq_war_path):
        if os.path.exists(deploy_path):
            shutil.copy(iiq_war_path, deploy_path)
        else:
            raise FileNotFoundError("Tomcat webapps deployment path not found.")
    else:
        raise FileNotFoundError("IIQ WAR file not found.")

    # Import the IIQ initialization files
    initialize_iiq("sp.init-custom.xml")

    if extend_schema:
        install_iiq_extended_schema()


def install_iiq_extended_schema():
    """
    Install the IdentityIQ extended schema by running the iiq extendedSchema 
    command, then initialize the database tables with the 
    add_identityiq_extensions.postgresql script.
    """
    logger.info("Extending database schema...")
    print("Extending database schema...")
    iiq_base = os.environ['CATALINA_BASE']
    iiq_wi_path = os.path.join(iiq_base, 'webapps', 'identityiq', 'WEB-INF')

    iiq = get_iiq_script()
    if os.path.exists(iiq_wi_path):
    
        iiq_out = subprocess.Popen([iiq, 'extendedSchema'],
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT)

        stdout, stderr = iiq_out.communicate()

        if stderr:
            logger.error("Error during extended schema initialization.")
            print("Error during extended schema initialization.")
            logger.error(stderr.decode())
        else:
            logger.info("Extended schema initialization completed.")
            print("Extended schema initialization completed.")
            logger.info(stdout.decode())

        # add_identityiq_extensions.postgresql
        # location: $CATALINA_BASE\webapps\identityiq\WEB-INF\database\add_identityiq_extensions.postgresql
        extend_iiq_db_path = os.path.join(iiq_wi_path, 'database', 'add_identityiq_extensions.postgresql')
        install_db_schema(extend_iiq_db_path, database='identityiq')


def backup_db(database: str):
    logger.info("Backup database...")
    backup_path = os.environ['BACKUP_HOME']

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


def build_iiq(war: bool = True):
    ssb_home = os.environ['SSB_HOME']
    build = get_build_script()
    initialize_sphome()

    if os.path.exists(os.path.join(ssb_home, 'build', 'extract')):
        logger.info("Running build clean...")
        print("Running build clean...")
        # Run build clean
        bd_out = subprocess.Popen([build, "clean"],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)

        stdout, stderr = bd_out.communicate()

        if stderr:
            logger.error("Error during build clean... ")
            logger.error(stderr.decode())
        else:
            logger.info(stdout.decode())

    if war:
        # Run build
        logger.info("Building war...")
        print("Building war...")
        bd_out = subprocess.Popen([build, "war"],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
    
        stdout, stderr = bd_out.communicate()

        if stderr:
            logger.error("Error during build...")
            logger.error(stderr.decode())
        else:
            logger.info("IdentityIQ build completed.")
            print("IdentityIQ build completed.")
            logger.info(stdout.decode())

    else:
        # Run build to extract the database schema
        logger.info("Building IdentityIQ...")
        print("Building IdentityIQ...")
        bd_out = subprocess.Popen([build],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
    
        stdout, stderr = bd_out.communicate()

        if stderr:
            logger.error("Error during build...")
            logger.error(stderr.decode())
        else:
            logger.info("IdentityIQ build completed.")
            logger.info(stdout.decode())


def copy_update_iiq_properties(db_hostname: str = 'db'):
    logger.info("Copying IdentityIQ property files...")

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

    # Copy sandbox.target.properties to <instance_name>.target.properties
    src_target = os.path.join(ssb_home, 'sandbox.target.properties')
    dest_target = os.path.join(ssb_home, inst_name + '.target.properties')

    if not os.path.exists(dest_target):
        shutil.copyfile(src_target, dest_target)


def create_database(database: str = 'postgres'):
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


def get_build_script() -> str:
    os.environ['SPTARGET'] = os.environ['INSTANCE_NAME']
    ssb_home = os.environ['SSB_HOME']
    build_script = os.path.join(ssb_home, 'build.sh')
    if not os.path.exists(build_script):
        logger.info("Build script not found.")
        raise FileNotFoundError("Build script not found.")
    else:
        if not os.access(build_script, os.X_OK):
            os.chmod(build_script, 0o750)

        return build_script


def get_iiq_script() -> str:
    iiq_base = os.environ['CATALINA_BASE']
    iiq_home = os.path.join(iiq_base, 'webapps', 'identityiq')
    while not os.path.exists(iiq_home):
        logger.info("Waiting for IIQ to be deployed...")
        time.sleep(3)

    iiq_script = os.path.join(iiq_home, 'WEB-INF', 'bin', 'iiq')
    if not os.access(iiq_script, os.X_OK):
        os.chmod(iiq_script, 0o750)

    # Set CLASSPATH 
    iiq_wi_path = os.path.join(iiq_home, 'WEB-INF')
    if 'CLASSPATH' in os.environ:
        os.environ['CLASSPATH'] = f"{os.getenv('CLASSPATH')}:{iiq_wi_path}/classes:{iiq_wi_path}/lib/identityiq.jar"

    if os.path.exists(iiq_script):
        return iiq_script
    else:
        raise FileNotFoundError("IIQ script not found.")


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
    tomcat_host = os.uname().nodename
    if not tls_port:
        tls_port = '8443'

    tomcat_url = f'https://{tomcat_host}:{tls_port}/manager/text/'

    return tomcat_url


def get_tomcat_mgr_credentials() -> str:
    rpauser_pass_path = os.path.join(os.environ['SECRETS_HOME'], 'rpauser.pass')
    if os.path.exists(rpauser_pass_path):
        with open(rpauser_pass_path, 'r') as f:
            rpauser_pass = f.read().strip()

        if rpauser_pass:
            return rpauser_pass
        else:
            raise ValueError("RPA user password file is empty.")
    else:
        raise FileNotFoundError("RPA user password file not found.")
    

def initialize_iiq(init_file: str = 'init.xml'):
    """
    Run the post-install initialization script to set up IIQ after the WAR 
    file has been deployed and the application is running.
    """
    logger.info("Initialization IdentityIQ...")
    print("Initialization IdentityIQ...")
    
    iiq_base = os.environ['CATALINA_BASE']
    iiq_wi_path = os.path.join(iiq_base, 'webapps', 'identityiq', 'WEB-INF')
    iiq = get_iiq_script()

    # IdentityIQ initialization file to be imported
    init_xml_path = f"{iiq_wi_path}/config/{init_file}"

    # Create the file for automating import
    bk_path = os.environ['BACKUP_HOME']
    import_inits_path = os.path.join(bk_path, 'import-inits.txt')

    if not os.path.exists(import_inits_path):
        with open(import_inits_path, 'w') as f:
            f.write('import ' + init_xml_path + '\n')

    iiq_out = subprocess.Popen([iiq, 'console', '-f', import_inits_path],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)

    stdout, stderr = iiq_out.communicate()

    if stderr:
        logger.error("Error during initialization...")
        logger.error(stderr.decode())
    else:
        logger.info("Initialization completed.")
        print("Initialization completed.")   
        logger.info(stdout.decode())


def initialize_sphome():
    if not 'SPHOME' in os.environ:
        webapps_base = os.path.join(os.environ['CATALINA_BASE'], 'webapps')
        sphome = os.path.join(webapps_base, 'identityiq')

        # Set SPHOME environment variable to the path of the deployed IdentityIQ 
        # application
        os.environ['SPHOME'] = sphome


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


def update_iiq_properties(prop_file_path: str, db_hostname: str = 'db'):
    logger.info("Updating IdentityIQ properties...")
    ssb_home = os.environ['SSB_HOME']
    iiq_properties_path = os.path.join(ssb_home, prop_file_path)

    # Update the IdentityIQ properties database connection settings
    match_term = r'devsrv'
    replace_term = f'{db_hostname}'

    with open(iiq_properties_path, 'r') as f:
        iiq_properties = f.read()

    iiq_properties = re.sub(match_term, replace_term, iiq_properties)

    with open(iiq_properties_path, 'w') as f:
        f.write(iiq_properties)

    logger.info("IdentityIQ properties updated.")


def update_log4j2_properties(log4j2_prop_path: str):
    logger.info("Updating log4j2 properties...")
    ssb_home = os.environ['SSB_HOME']
    log4j2_properties_path = os.path.join(ssb_home, log4j2_prop_path)

    # Update the log4j2 properties to write logs to the instance logs directory
    match_term = r'env:TC_INSTANCE'
    replace_term = r'env:INSTANCE_NAME'

    with open(log4j2_properties_path, 'r') as f:
        log4j2_properties = f.read()

    log4j2_properties = re.sub(match_term, replace_term, log4j2_properties)

    with open(log4j2_properties_path, 'w') as f:
        f.write(log4j2_properties)
    
    logger.info("Log4j2 properties updated.")


if __name__ == '__main__':
    main(sys.argv[1:])