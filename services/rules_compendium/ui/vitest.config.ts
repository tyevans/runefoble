import { domTestConfig } from '../../../vitest.dom.config.ts';
import { loopbackUpstreamCommands } from '../../../libs/runefoble_ui/testing/loopback-commands.ts';

export default domTestConfig(import.meta.dirname, { commands: loopbackUpstreamCommands });
