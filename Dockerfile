FROM kbase/sdkbase2:python
MAINTAINER KBase Developer
# -----------------------------------------
# In this section, you can install any system dependencies required
# to run your App.  For instance, you could place an apt-get update or
# install line here, a git checkout to download code, or run any other
# installation scripts.

# RUN apt-get update

COPY ./requirements.txt /tmp
RUN pip install --upgrade pip && \
	pip install -r /tmp/requirements.txt

# download validator files
RUN VALIDATOR_COMMIT='701825e0627aad865d00256b05bc89f39cf7052d' && \
		cd /kb/deployment/bin && \
		git clone https://github.com/kbase/sample_service_validator_config.git && \
    cd sample_service_validator_config && \
    git checkout ${VALIDATOR_COMMIT}

# -----------------------------------------

COPY ./ /kb/module
RUN mkdir -p /kb/module/work
RUN chmod -R a+rw /kb/module

WORKDIR /kb/module
RUN make all

ENTRYPOINT [ "./scripts/entrypoint.sh" ]

CMD [ ]
