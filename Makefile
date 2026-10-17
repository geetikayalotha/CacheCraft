.PHONY: compile python native demo clean

compile: python native

python:
	python -m compileall -q cachecraft

native:
	cd craft && go build ./...

demo:
	python -m cachecraft --help

clean:
	@echo Cleaning generated report artifacts

