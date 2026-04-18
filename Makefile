.PHONY: help # print this help list
help:
	grep PHONY Makefile | sed 's/.PHONY: /make /' | grep -v grep

.PHONY: clean # remove packaging files
clean:
	find . -iname "__pycache__" | while read d; do rm -rf $$d; done

.PHONY: major minor patch # update version, CHANGELOG.md and push with also tags
major:
	$(MAKE) release PART=major

minor:
	$(MAKE) release PART=minor

patch:
	$(MAKE) release PART=patch

release:
	bump-my-version bump $(PART)
	git-cliff --config pyproject.toml --output CHANGELOG.md
	sed -i 's/<!-- [0-9]* -->//g' CHANGELOG.md
	git add CHANGELOG.md
	git commit --amend --no-edit
	git tag -f v$$(python -c "from src import __version__; print(__version__)")
	git push && git push --tags --force

.PHONY: changelog # update CHANGELOG.md and amend it on the commit
changelog:
	git-cliff --config pyproject.toml --output CHANGELOG.md
	sed -i 's/<!-- [0-9]* -->//g' CHANGELOG.md
	git add CHANGELOG.md
	git commit --amend --no-edit

.PHONY: loopback_redirect # create loopback sink and redirect audio of APP=<binary>; pass MONITOR=1 to also hear it on the default sink
loopback_redirect:
	@if [ -z "$(APP)" ]; then \
		echo "Usage: make loopback_redirect APP=<binary> [MONITOR=1]  (e.g. APP=firefox)"; \
		exit 1; \
	fi
	@pactl list short modules | grep -q 'sink_name=loopback' || \
		pactl load-module module-null-sink sink_name=loopback sink_properties=device.description=Loopback >/dev/null
	@pactl list sink-inputs | awk -v app="$(APP)" '/^Sink Input #/ {id=substr($$3, 2)} index($$0, "application.process.binary = \"" app "\"") {print id}' | \
		xargs -r -I{} pactl move-sink-input {} loopback
	@if [ "$(MONITOR)" = "1" ]; then \
		pactl list short modules | grep -q 'module-loopback.*source=loopback.monitor' || \
			pactl load-module module-loopback source=loopback.monitor sink=$$(pactl get-default-sink) latency_msec=50 >/dev/null; \
		echo "Loopback ready for $(APP) with monitoring on default sink."; \
	else \
		echo "Loopback ready for $(APP) (silent; use MONITOR=1 to also hear it)."; \
	fi
	@echo "Find device ID with: uv run python -m audio_client --list-devices | grep -i loop"

.PHONY: loopback_clean # restore audio streams routed to loopback and unload the null-sink (plus any monitor bridge)
loopback_clean:
	@LOOP_SINK=$$(pactl list short sinks | awk '/\tloopback\t/ {print $$1}'); \
	LOOP_MOD=$$(pactl list short modules | awk '/sink_name=loopback/ {print $$1}'); \
	MON_MOD=$$(pactl list short modules | awk '/module-loopback.*source=loopback.monitor/ {print $$1}'); \
	DEFAULT=$$(pactl get-default-sink); \
	if [ -n "$$LOOP_SINK" ]; then \
		pactl list short sink-inputs | awk -v s=$$LOOP_SINK '$$2==s {print $$1}' | \
			xargs -r -I{} pactl move-sink-input {} "$$DEFAULT"; \
	fi; \
	if [ -n "$$MON_MOD" ]; then \
		pactl unload-module $$MON_MOD; \
	fi; \
	if [ -n "$$LOOP_MOD" ]; then \
		pactl unload-module $$LOOP_MOD; \
	fi
