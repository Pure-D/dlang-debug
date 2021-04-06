# dlang-debug

Pretty printers for various dlang types for GDB, LLDB and VSDBG.

TODO:
- GDB
  - [ ] Test on all OS
    - [x] Linux
    - [ ] OSX
    - [ ] Windows
  - [x] Associative Arrays
  - [x] Arrays
  - [x] Strings (bug: doesn't respect length, stops at null characters)
  - [ ] phobos types (tbd)
- LLDB
  - [ ] Test on all OS
    - [x] Linux
    - [ ] OSX
    - [x] ~~Windows~~ -> broken with LDC
  - [x] Associative Arrays
  - [x] Arrays
  - [x] Strings
  - [ ] phobos types (tbd)
- VSDBG (NatVis)
  - [x] Windows Support only
  - [ ] Test with all Compilers
    - [x] LDC `-gc`
    - [x] ~~LDC `-g`~~ -> broken, not implementable
    - [ ] DMD `-gc`
    - [ ] DMD `-g`
  - [x] Associative Arrays
  - [x] Arrays
  - [x] Strings
  - [ ] phobos types (tbd)

Due to the pretty printing API, LLDB offers better type displays.

Boilerplate code for LLDB taken from [vscode-lldb](https://github.com/vadimcn/vscode-lldb).

## Usage

### Automatic with any installed debugger

**VSCode with [webfreak.code-d](https://marketplace.visualstudio.com/items?itemName=webfreak.code-d)**

(recommends extensions C/C++ on Windows or CodeLLDB on other platforms installed)

```js
{
	"name": "Debug Program",
	"request": "launch",
	"type": "code-d",
	"program": "${command:dubTarget}",
	"cwd": "${workspaceFolder}",
	"dubBuild": true // optional, automatic builds
}
```

code-d has these debug configurations bundled since version 0.23.0 and automatically detects the recommended settings for the current platform with the installed debug extensions.

### GDB

Enable pretty printers and source the gdb_dlang.py script.

MI Commands (for use with extensions):

```
-enable-pretty-printing
-interpreter-exec console "source /path/to/gdb_dlang.py"
```

**VSCode Debug Extension Configurations:**

**C/C++ (ms-vscode.cpptools)**

```json
{
	"name": "Debug Program",
	"request": "launch",
	"type": "cppdbg",
	"program": "${workspaceFolder}/programname",
	"cwd": "${workspaceFolder}",
	"setupCommands": [
		{
			"description": "Enable python pretty printing",
			"ignoreFailures": false,
			"text": "-enable-pretty-printing"
		},
		{
			"description": "Load D GDB type extensions",
			"ignoreFailures": false,
			"text": "-interpreter-exec console \"source /path/to/gdb_dlang.py\""
		}
	]
}
```

**NativeDebug (webfreak.code-debug)**

```json
{
	"name": "Debug Program",
	"request": "launch",
	"type": "gdb",
	"target": "./programname",
	"cwd": "${workspaceFolder}",
	"autorun": [
		"source /path/to/gdb_dlang.py"
	],
	"valuesFormatting": "prettyPrinters"
}
```

### LLDB

Import the lldb script:

```
command script import "/path/to/lldb_dlang.py"
```

**VSCode Debug Extension Configurations:**

**CodeLLDB (vadimcn.vscode-lldb)**

```json
{
	"name": "Debug Program",
	"request": "launch",
	"type": "lldb",
	"program": "${workspaceFolder}/programname",
	"cwd": "${workspaceFolder}",
	"initCommands": ["command script import \"/path/to/lldb_dlang.py\""]
}
```

### NatVis with VSDBG

**Visual Studio:**

Put the natvis file in your workspace, it will be loaded automatically and just work.

**VSCode Debug Extension Configurations:**

**C/C++ (ms-vscode.cpptools)**

```json
{
	"name": "Debug Program",
	"request": "launch",
	"type": "cppvsdbg",
	"program": "${workspaceFolder}/programname.exe",
	"cwd": "${workspaceFolder}",
	"visualizerFile": "C:\\Path\\To\\dlang.natvis"
}
```
