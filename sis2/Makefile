PROTO_ROOT := shared/src

.PHONY: proto
proto:
	uv run python -m grpc_tools.protoc -I$(PROTO_ROOT) \
		--python_out=$(PROTO_ROOT) --pyi_out=$(PROTO_ROOT) --grpc_python_out=$(PROTO_ROOT) \
		$(PROTO_ROOT)/shared/proto/counters.proto
