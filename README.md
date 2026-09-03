# An Apache Tomcat Java Build Container

This is an Apache Tomcat 9 OpenJDK 21 Docker image based on the Avium Labs 
tomcat:9.0.nnn-alpine image.

GitHub: https://github.com/aviumlabs/tomcat-img

This image includes Apache Ant and ant-contrib.

Current Apache Tomcat version: 9.0.121

## Build an Image

### Build Default

```
export TC_VERSION=9.0.121
```

**Regular build**  
```
docker build --pull --no-cache -t aviumlabs/tomcat-ant:$TC_VERSION-alpine .
```

**Build with sbom and provenance** 
```
docker build --pull --no-cache -t aviumlabs/tomcat-ant:$TC_VERSION-alpine --provenance=mode=max --sbom=true .
```

```
export INST_NAME=tc1
```

```
docker run -h ap2.aviumlabs.test --name ap2 -p 8080:8080 -p 8443:8443 -v ap2_tc_backup:/opt/backup -v ap2_tc_inst_logs:/opt/tomcat/instances/$INST_NAME/logs -v ap2_tc_inst_conf:/opt/tomcat/instances/$INST_NAME/conf -v ap2_tc_secrets:/opt/secrets -v ap2_tc_inst_webapps:/opt/tomcat/instances/$INST_NAME/webapps -it --rm aviumlabs/tomcat-ant:$TC_VERSION-alpine
```

Push to docker hub:
```
docker push aviumlabs/tomcat-ant:$TC_VERSION-alpine
```

## Runtime

```
docker exec -it ap2 /bin/ash
```

```
java --version
```

>  
> openjdk 21.0.12 2026-07-21  
> OpenJDK Runtime Environment (build 21.0.12+8-alpine-r0)  
> OpenJDK 64-Bit Server VM (build 21.0.12+8-alpine-r0, mixed mode, sharing)
>  

```
psql --version
```

>  
> psql (PostgreSQL) 18.6  
>  


## Ant Home

/usr/share/java/apache-ant/

**Ant Libraby Path**

/usr/share/java/apache-ant/lib