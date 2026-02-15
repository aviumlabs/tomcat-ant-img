# syntax=docker/dockerfile:1
FROM aviumlabs/tomcat:9.0.113-alpine

ENV ANT_HOME=/usr/share/java/apache-ant
ENV PATH="${ANT_HOME}/bin:${PATH}"
ENV PG_HOST=db
ENV PG_PORT=5432
ENV PG_USER=postgres
ENV PG_DB=postgres


USER root

RUN apk add --no-cache \
    apache-ant \
    postgresql18-client \
    vim

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

COPY deptools.py /usr/local/bin/deptools.py
RUN chown tomcat:tomcat /usr/local/bin/deptools.py \
    && chmod +x /usr/local/bin/deptools.py \
    && touch /opt/backup/deptools.log \
    && chown tomcat:tomcat /opt/backup/deptools.log

USER tomcat

CMD ["/bin/ash"]