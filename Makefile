SERVICE_TITLE=Various text formats to Markdown Conversion

PROJECT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
PORT=8077
SERVICE_URL=http://localhost:${PORT}

run:
	poetry ivcap run -- --port ${PORT}

REQUEST=tests/request.json
test-local:
	curl -i -X POST \
		-H "content-type: application/json" \
		-H "authorization: Bearer $(shell ivcap context get access-token --refresh-token)" \
		-H "timeout: 600" \
		--data @${REQUEST} \
		${SERVICE_URL}

test-job:
	poetry ivcap job-exec ${REQUEST}

docker-build:
	poetry ivcap docker-build

docker-run:
	poetry ivcap docker-run -- --port ${PORT}

.PHONY: run
