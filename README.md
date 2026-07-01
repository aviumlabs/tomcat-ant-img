# An Apache Tomcat Java Build Container

This is an Apache Tomcat 9 OpenJDK 21 Docker image based on the Avium Labs 
tomcat:9.0.nnn-alpine image.

GitHub: https://github.com/aviumlabs/tomcat-img

This image includes Apache Ant and ant-contrib.

Current Apache Tomcat version: 9.0.119



## Build an Image

### Build Default

```shell
export TC_VERSION=9.0.119
```

**Regular build**  
```shell
docker build --pull --no-cache -t aviumlabs/tomcat-ant:$TC_VERSION-alpine .
```

**Build with sbom and provenance** 
```shell
docker build --pull --no-cache -t aviumlabs/tomcat-ant:$TC_VERSION-alpine --provenance=mode=max --sbom=true .
```

```shell
export INST_NAME=tc1
```

```shell
docker run -h ap2.aviumlabs.test --name ap2 -p 8080:8080 -p 8443:8443 -v ap2_tc_backup:/opt/backup -v ap2_tc_inst_logs:/opt/tomcat/instances/$INST_NAME/logs -v ap2_tc_inst_conf:/opt/tomcat/instances/$INST_NAME/conf -v ap2_tc_secrets:/opt/secrets -v ap2_tc_inst_webapps:/opt/tomcat/instances/$INST_NAME/webapps -it --rm aviumlabs/tomcat-ant:$TC_VERSION-alpine
```

Push to docker hub:
```shell 
docker push aviumlabs/tomcat-ant:$TC_VERSION-alpine
```

## Runtime

```shell
docker exec -it ap2 /bin/ash
```

## Ant Home

/usr/share/java/apache-ant/

**Ant Libraby Path**

/usr/share/java/apache-ant/lib