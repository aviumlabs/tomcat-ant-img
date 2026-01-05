# syntax=docker/dockerfile:1
FROM aviumlabs/tomcat:9.0.113-alpine

ENV ANT_HOME=/usr/share/java/apache-ant
ENV PATH="${ANT_HOME}/bin:${PATH}"

USER root

RUN apk add --no-cache \
    apache-ant

RUN set -xe \
	&& CONTRIB_DOWNLOAD_URL="https://sourceforge.net/projects/ant-contrib/files/ant-contrib/1.0b3/ant-contrib-1.0b3-bin.tar.gz/download" \
	&& CONTRIB_DOWNLOAD_MD5="ee06ff88da133dce3acc3248aee0ad83" \
    && apk add --no-cache --virtual .fetch-deps \
		curl \
		ca-certificates \
    && curl -fSL -o ant-contrib.tar.gz "$CONTRIB_DOWNLOAD_URL" \
    && echo "$CONTRIB_DOWNLOAD_MD5  ant-contrib.tar.gz" | md5sum -c - \
    && tar -xzf ant-contrib.tar.gz ant-contrib/ant-contrib-1.0b3.jar -C ${ANT_HOME}/lib --strip-components=1 \
    && rm ant-contrib.tar.gz \
    && apk del .fetch-deps  

USER tomcat

CMD ["/bin/ash"]