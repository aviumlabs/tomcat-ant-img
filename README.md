# An Apache Tomcat Java Build Container

This is an Apache Tomcat 9 OpenJDK 21 Docker image based on the Avium Labs 
tomcat:9.0.113-alpine image.

This image includes Apache Ant and ant-contrib.


## Build an Image

### Build Default

**Regular build**  
```shell
docker build --pull --no-cache -t aviumlabs/tomcat-ant:9.0.113-alpine .
```

**Build with sbom and provenance** 
```shell
docker build --pull --no-cache -t aviumlabs/tomcat-ant:9.0.113-alpine --provenance=mode=max --sbom=true .
```

```shell
docker run -h ap2 --name ap2 -p 8080:8080 -p 8443:8443 -v ap2_tc_backup:/opt/backup -v ap2_tc_inst_logs:/opt/tomcat/instances/bin-a/logs -v ap2_tc_inst_conf:/opt/tomcat/instances/bin-a/conf -v ap2_tc_secrets:/opt/secrets -v ap2_tc_inst_webapps:/opt/tomcat/instances/bin-a/webapps -it --rm aviumlabs/tomcat-ant:9.0.113-alpine
```

Push to docker hub:
```shell 
docker push aviumlabs/tomcat-ant:9.0.113-alpine
```

## Ant Home

/usr/share/java/apache-ant/

**Ant Libraby Path**

/usr/share/java/apache-ant/lib