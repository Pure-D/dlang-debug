# dlang-debug

Pretty printers for various dlang types for GDB and LLDB.

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
    - [ ] Windows
  - [x] Associative Arrays
  - [x] Arrays
  - [x] Strings
  - [ ] phobos types (tbd)

Due to the pretty printing API, LLDB offers better type displays.

Boilerplate code for LLDB taken from [vscode-lldb](https://github.com/vadimcn/vscode-lldb).

## Usage

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

