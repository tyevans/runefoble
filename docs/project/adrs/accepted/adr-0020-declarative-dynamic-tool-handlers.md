# ADR-0020: Declarative Dynamic Tool Handlers

## Status
Accepted

## Context
A dynamic MCP tool carried a Python `handler_code` string. The MCP gateway ran it with `exec` in its own process. An AST check and a reduced builtins table were the only protection. Restricted `exec` sandboxes in CPython are often escaped. One registered tool could run arbitrary code with the gateway credentials, including the service credential (ADR-0015 (e)). The authorization checks `mcp_tool.manage` and `mcp_tool.execute` (ADR-0001) control who registers and runs a tool. They do not make the code safe.

Two options were considered (TASK-0766):

- **Option A. Declarative handlers.** A tool definition is data. No user code runs.
- **Option B. Isolated runtime.** User code runs in a separate process or container with no network, no secrets, CPU and memory limits, and a time-out.

## Decision
We choose **Option A**.

Reasoning:
- No product need for user code exists. The product records (PRD-0022) and all registered tools in the test suite compute dice results, damage falloff, and small result objects from numeric arguments. A template, arithmetic, and dice cover them.
- Option B adds a runtime to deploy (process or container, limits, image, orchestration) for a need that does not exist. It also keeps a code-execution surface.
- Option A removes the risk class. The gateway never compiles or runs text from a caller.

Design:
1. `DynamicToolDefinition.handler` is a required, non-empty JSON object. The `handler_code` and `sandbox_policy` fields are removed. No compatibility path exists (DoR 9).
2. The handler is a result template. The tool returns the template after evaluation:
   - A string that is exactly `${name}` becomes the argument `name`, with its type kept.
   - A string with embedded `${name}` text becomes a string with the argument value inserted.
   - `{"$expr": "<expression>"}` becomes the number that the expression gives. An expression allows numbers, argument names, `+ - * / // %`, unary signs, parentheses, and the functions `max`, `min`, `abs`, and `round`. A small interpreter walks a parsed tree. The gateway never calls `eval` or `exec`.
   - `{"$dice": "NdS+M"}` becomes the total of N rolls of an S-sided die plus the modifier M.
   - An object or a list becomes an object or a list of evaluated values.
   - Any other `$` key is refused.
3. Registration checks the whole handler. Every name must be a declared parameter. Expression length, node count, dice count, dice sides, and template depth have fixed limits. A violation returns HTTP 400. The tool is not added.
4. Calls from one tool to other registered tools are not part of this decision. They need a call-depth rule and per-call authorization (TASK-0545). A new ADR must cover them.

## Consequences
- No `exec` or `eval` of caller input remains in `gateway/mcp`. `gateway_mcp/sandbox.py` is deleted.
- A tool author cannot write loops, branches, or helper functions. If a real need appears, a new ADR must choose Option B or extend the expression language.
- Every handler runs in bounded time and memory, so a separate time-limit task (TASK-0737) has no code-handler case to cover.
- Docs and tests that use `handler_code` change in the same commit.
