import gdb.printing

class DCStringPrinter(object):
	"print D string values"

	def __init__(self, val):
		self.val = val

	def display_hint(self):
		return 'string'

	def to_string(self):
		length = int(self.val['length'])
		return self.val['ptr'].cast(gdb.lookup_type("char").pointer()).string('utf-8', length = length)

class DWStringPrinter(object):
	"print D wstring values"

	def __init__(self, val):
		self.val = val

	def display_hint(self):
		return 'string'

	def to_string(self):
		length = int(self.val['length'])
		return self.val['ptr'].cast(gdb.lookup_type("wchar").pointer()).string('utf-16', length = length)

class DDStringPrinter(object):
	"print D dstring values"

	def __init__(self, val):
		self.val = val

	def display_hint(self):
		return 'string'

	def to_string(self):
		length = int(self.val['length'])
		return self.val['ptr'].cast(gdb.lookup_type("dchar").pointer()).string('utf-32', length = length)

class DArrayPrinter(object):
	"print D arrays"

	def __init__(self, val):
		self.val = val

	def display_hint(self):
		return 'array'

	def length(self):
		return int(self.val['length'])

	def ptr(self):
		return self.val['ptr']

	def to_string(self):
		return '[' + str(self.length()) + '] @ ' + str(self.ptr())

	def children(self):
		length = self.length()
		ptr = self.ptr()
		for i in range(length):
			yield str(i), ptr[i]

class DAssocArrayPrinter(object):
	"print D associative arrays"

	def __init__(self, val):
		self.val = val
		self.key_type = gdb.lookup_type("void")
		self.value_type = gdb.lookup_type("void")

		tag = val.type.tag
		if tag != None:
			if tag.startswith("_AArray_"):
				self.parse_types_dmd(tag)
			elif tag.endswith("]"):
				self.parse_types_ldc(tag)

	def display_hint(self):
		return 'array'

	def parse_types_dmd(self, tag):
		# splits an AA type like _AArray_ucent_int into key & value
		tag = tag[8:]
		# https://github.com/dlang/dmd/blob/7a0382177f35b2766c2d0ba60dae5e541d8033e0/src/dmd/backend/var.d#L297
		if tag.startswith('_'):
			# types might start with _, but there is no type starting with _ which is less than 3 characters long
			# so we start searching for _ starting on the 3rd character
			split_loc = tag.find('_', 2)
		else:
			split_loc = tag.find('_')

		if split_loc != -1:
			# however some types end with _t, so we need to offset the splitter by 2
			if tag[split_loc:].startswith('_t_'):
				split_loc += 2

			key_str = tag[0:split_loc]
			value_str = tag[(split_loc+1):]
			if key_str != 'key':
				self.key_type = parse_dmd_type(key_str)
			if value_str != 'value':
				self.value_type = parse_dmd_type(value_str)

	def parse_types_ldc(self, tag):
		key_start = len(tag)
		depth = 0
		while key_start >= 0:
			key_start -= 1
			if tag[key_start] == ']':
				depth += 1
			elif tag[key_start] == '[':
				depth -= 1
			if depth == 0:
				break
		self.value_type = parse_d_type(tag[:key_start])
		self.key_type = parse_d_type(tag[(key_start+1):-1])

	# assumed ABI:
	# struct AA
	#   Bucket[] buckets
	#   uint used
	#   uint deleted
	#   void* entryTI
	#   uint firstUsed
	#   uint keysz
	#   uint valsz
	#   uint valoff
	#   ubyte flags
	#
	# struct Bucket (align 16)
	#   size_t hash
	#   void* entry

	def used(self):
		# *(uint*)((void*)ptr + 16)
		# (uint)ptr@16
		return (self.val['ptr'].cast(gdb.lookup_type("void").pointer()) + gdb.lookup_type("size_t").alignof * 2).cast(gdb.lookup_type("uint").pointer()).dereference()

	def deleted(self):
		return (self.val['ptr'].cast(gdb.lookup_type("void").pointer()) + gdb.lookup_type("size_t").alignof * 2 + gdb.lookup_type("uint").alignof).cast(gdb.lookup_type("uint").pointer()).dereference()

	def valoff(self):
		return (self.val['ptr'].cast(gdb.lookup_type("void").pointer()) + gdb.lookup_type("size_t").alignof * 3 + gdb.lookup_type("uint").alignof * 5).cast(gdb.lookup_type("uint").pointer()).dereference()

	def buckets(self):
		"returns an iterator of bucket pointers"

		# *(size_t*)ptr
		length = self.val['ptr'].cast(gdb.lookup_type("size_t").pointer()).dereference()
		# (void*)ptr@8
		bucketptr = self.val['ptr'].cast(gdb.lookup_type("void").pointer()) + gdb.lookup_type("size_t").alignof
		bucketptr = bucketptr.cast(gdb.lookup_type("void").pointer().pointer()).dereference()
		bucketsize = self.bucket_size()

		for i in range(length):
			yield bucketptr + (i * bucketsize)

	def bucket_filled(self, bucket):
		hashval = bucket.cast(gdb.lookup_type("size_t").pointer()).dereference()
		HASH_FILLED_MARK = 1 << (8 * gdb.lookup_type("size_t").alignof) - 1
		return hashval & HASH_FILLED_MARK != 0

	def bucket_entry(self, bucket):
		# *(void**)bucket@8
		ret = bucket.cast(gdb.lookup_type("void").pointer()) + gdb.lookup_type("size_t").alignof
		return ret.cast(gdb.lookup_type("void").pointer().pointer()).dereference()

	def bucket_size(self):
		return gdb.lookup_type("void").pointer().alignof + gdb.lookup_type("size_t").alignof

	def length(self):
		return self.used() - self.deleted()

	def to_string(self):
		return '[' + str(self.length()) + ']'

	def children(self):
		off = self.valoff()
		for bucket in self.buckets():
			if self.bucket_filled(bucket):
				entry = self.bucket_entry(bucket)
				yield reinterpret_aa_key(entry, self.key_type), reinterpret_aa_val(entry + off, self.value_type)

def reinterpret_aa_key(value, type):
	if type.name == 'void':
		return '[(void*) %s]' % str(value.cast(type.pointer()))
	else:
		return str(value.cast(type.pointer()).dereference())

def reinterpret_aa_val(value, type):
	if type.name == 'void':
		return value.cast(type.pointer())
	else:
		return value.cast(type.pointer()).dereference()

def parse_d_type(type):
	return gdb.lookup_type(type)

def parse_dmd_type(type):
	return {
		"bool": gdb.lookup_type("bool"),
		"char": gdb.lookup_type("char"),
		"signed char": gdb.lookup_type("byte"),
		"unsigned char": gdb.lookup_type("ubyte"),
		"char8_t": gdb.lookup_type("char"),
		"char16_t": gdb.lookup_type("wchar"),
		"short": gdb.lookup_type("short"),
		"wchar_t": gdb.lookup_type("wchar"),
		"unsigned short": gdb.lookup_type("ushort"),
		"enum": gdb.lookup_type("uint"),
		"int": gdb.lookup_type("int"),
		"unsigned": gdb.lookup_type("uint"),
		"long": gdb.lookup_type("int"),
		"unsigned long": gdb.lookup_type("uint"),
		"dchar": gdb.lookup_type("dchar"),
		"long long": gdb.lookup_type("long"),
		"uns long long": gdb.lookup_type("ulong"),
		"cent": gdb.lookup_type("void"),
		"ucent": gdb.lookup_type("void"),
		"float": gdb.lookup_type("float"),
		"double": gdb.lookup_type("double"),
		"double alias": gdb.lookup_type("double"),
		"long double": gdb.lookup_type("real"),
		"imaginary float": gdb.lookup_type("ifloat"),
		"imaginary double": gdb.lookup_type("idouble"),
		"imaginary long double": gdb.lookup_type("ireal"),
		"complex float": gdb.lookup_type("cfloat"),
		"complex double": gdb.lookup_type("cdouble"),
		"complex long double": gdb.lookup_type("creal"),
		"float[4]": gdb.lookup_type("float").vector(4 - 1),
		"double[2]": gdb.lookup_type("double").vector(2 - 1),
		"signed char[16]": gdb.lookup_type("byte").vector(16 - 1),
		"unsigned char[16]": gdb.lookup_type("ubyte").vector(16 - 1),
		"short[8]": gdb.lookup_type("short").vector(8 - 1),
		"unsigned short[8]": gdb.lookup_type("ushort").vector(8 - 1),
		"long[4]": gdb.lookup_type("int").vector(4 - 1),
		"unsigned long[4]": gdb.lookup_type("uint").vector(4 - 1),
		"long long[2]": gdb.lookup_type("long").vector(2 - 1),
		"unsigned long long[2]": gdb.lookup_type("ulong").vector(2 - 1),
		"float[8]": gdb.lookup_type("float").vector(8 - 1),
		"double[4]": gdb.lookup_type("double").vector(4 - 1),
		"signed char[32]": gdb.lookup_type("byte").vector(32 - 1),
		"unsigned char[32]": gdb.lookup_type("ubyte").vector(32 - 1),
		"short[16]": gdb.lookup_type("short").vector(16 - 1),
		"unsigned short[16]": gdb.lookup_type("ushort").vector(16 - 1),
		"long[8]": gdb.lookup_type("int").vector(8 - 1),
		"unsigned long[8]": gdb.lookup_type("uint").vector(8 - 1),
		"long long[4]": gdb.lookup_type("long").vector(4 - 1),
		"unsigned long long[4]": gdb.lookup_type("ulong").vector(4 - 1),
		"float[16]": gdb.lookup_type("float").vector(16 - 1),
		"double[8]": gdb.lookup_type("double").vector(8 - 1),
		"signed char[64]": gdb.lookup_type("byte").vector(64 - 1),
		"unsigned char[64]": gdb.lookup_type("ubyte").vector(64 - 1),
		"short[32]": gdb.lookup_type("short").vector(32 - 1),
		"unsigned short[32]": gdb.lookup_type("ushort").vector(32 - 1),
		"long[16]": gdb.lookup_type("int").vector(16 - 1),
		"unsigned long[16]": gdb.lookup_type("uint").vector(16 - 1),
		"long long[8]": gdb.lookup_type("long").vector(8 - 1),
		"unsigned long long[8]": gdb.lookup_type("ulong").vector(8 - 1),
		"nullptr_t": gdb.lookup_type("void"),
		"*": gdb.lookup_type("void").pointer(),
		"&": gdb.lookup_type("void").reference(),
		"void": gdb.lookup_type("void"),
		"noreturn": gdb.lookup_type("void"),
		"struct": gdb.lookup_type("void"),
		"array": gdb.lookup_type("void"),
		"C func": gdb.lookup_type("void").pointer(),
		"Pascal func": gdb.lookup_type("void").pointer(),
		"std func": gdb.lookup_type("void").pointer(),
		"*": gdb.lookup_type("void").pointer(),
		"member func": gdb.lookup_type("void").pointer(),
		"D func": gdb.lookup_type("void").pointer(),
		"C func": gdb.lookup_type("void").pointer(),
		"__near &": gdb.lookup_type("void").reference(),
		"__ss *": gdb.lookup_type("void").pointer(),
		"__cs *": gdb.lookup_type("void").pointer(),
		"__far16 *": gdb.lookup_type("void").pointer(),
		"__far *": gdb.lookup_type("void").pointer(),
		"__huge *": gdb.lookup_type("void").pointer(),
		"__handle *": gdb.lookup_type("void").pointer(),
		"__immutable *": gdb.lookup_type("void").pointer(),
		"__shared *": gdb.lookup_type("void").pointer(),
		"__restrict *": gdb.lookup_type("void").pointer(),
		"__fg *": gdb.lookup_type("void").pointer(),
		"far C func": gdb.lookup_type("void").pointer(),
		"far Pascal func": gdb.lookup_type("void").pointer(),
		"far std func": gdb.lookup_type("void").pointer(),
		"_far16 Pascal func": gdb.lookup_type("void").pointer(),
		"sys func": gdb.lookup_type("void").pointer(),
		"far sys func": gdb.lookup_type("void").pointer(),
		"__far &": gdb.lookup_type("void").reference(),
		"interrupt func": gdb.lookup_type("void").pointer(),
		"memptr": gdb.lookup_type("void").pointer(),
		"ident": gdb.lookup_type("void"),
		"template": gdb.lookup_type("void"),
		"vtshape": gdb.lookup_type("void"),
	}.get(type, "void")

def build_pretty_printer():
	pp = gdb.printing.RegexpCollectionPrettyPrinter("dlang_utils")
	pp.add_printer('string', r'^_Array_char$|^_Array_char8_t$|^string$|^(?:const|immutable)?\(?char\)?\s*\[\]$', DCStringPrinter)
	pp.add_printer('wstring', r'^_Array_wchar_t$|^_Array_char16_t$|^wstring$|^(?:const|immutable)?\(?wchar\)?\s*\[\]$', DWStringPrinter)
	pp.add_printer('dstring', r'^_Array_dchar$|^dstring$|^(?:const|immutable)?\(?dchar\)?\s*\[\]$', DDStringPrinter)
	pp.add_printer('arrays', r'^_Array_|\[\]$', DArrayPrinter)
	pp.add_printer('hashmaps', r'^_AArray_|[^0-9\[][^\[]*\]$', DAssocArrayPrinter)
	return pp

gdb.printing.register_pretty_printer(gdb.current_objfile(), build_pretty_printer())

# # Register map:
# # fully qualified enum name -> {
# #   basetype: string,
# #   values: { [index: string]: gdb.Value }
# # }
# registeredEnums = {}
# class RegisterDlangEnum(gdb.Command):
# 	"""Register custom enums for debugging view (done by IDE)"""

# 	def __init__(self):
# 		super (RegisterDlangEnum, self).__init__("register-dlang-enum", gdb.COMMAND_DATA)

# 	def invoke(self, arg, from_tty):
# 		args = gdb.string_to_argv(arg)
# 		global registeredEnums

# 		if len(args) < 2 or len(args) % 2 != 0:
# 			raise Exception("Usage: register-dlang-enum [enum FQN] [basetype FQN] ([key value] ...)")
# 		else:
# 			enumfqn = args[0]
# 			basetype = args[1]
# 			values = {}
# 			try:
# 				for i in range(2, len(args), 2):
# 					values[args[i]] = gdb.parse_and_eval(args[i + 1])
# 				registeredEnums[enumfqn] = { "basetype": basetype, "values": values }
# 			except Exception as e:
# 				print("Ignoring values because failed to parse for enum: " + str(e))
# 				registeredEnums[enumfqn] = { "basetype": basetype }
# RegisterDlangEnum()

# class DFallbackEnumPrinter(object):
# 	"prints broken D enum values"

# 	def __init__(self, val):
# 		self.val = val

# 	def display_hint(self):
# 		return 'enum'

# 	def to_string(self):
# 		type = self.val.type
# 		if type.sizeof == 1:
# 			return 'cast(' + str(type) + ')' + str(self.val.address.cast(gdb.lookup_type("ubyte").pointer()).dereference())
# 		elif type.sizeof == 2:
# 			return 'cast(' + str(type) + ')' + str(self.val.address.cast(gdb.lookup_type("ushort").pointer()).dereference())
# 		elif type.sizeof == 4:
# 			return 'cast(' + str(type) + ')' + str(self.val.address.cast(gdb.lookup_type("uint").pointer()).dereference())
# 		elif type.sizeof == 8:
# 			return 'cast(' + str(type) + ')' + str(self.val.address.cast(gdb.lookup_type("ulong").pointer()).dereference())
# 		else:
# 			return 'cast(' + str(type) + ')<unknown>'

# class DRegisteredEnumPrinter(object):
# 	"prints an IDE registered D enum value"

# 	def __init__(self, val, register):
# 		self.val = val
# 		self.register = register
# 		self.basetype = gdb.lookup_type(register['basetype'])

# 	def display_hint(self):
# 		return 'enum'

# 	def to_string(self):
# 		type = str(self.val.type)
# 		val = self.val.address.cast(self.basetype.pointer()).dereference()
# 		moduleend = type.rfind('.')
# 		if moduleend != -1:
# 			type = type[(moduleend + 1):]
# 		if self.register['values'] != None:
# 			for named in self.register['values']:
# 				if self.register['values'][named] == val:
# 					return type + '.' + named + ' (' + str(val) + ')'
# 		return 'cast(' + type + ')' + str(val)

# def dlang_enum_printer(v):
# 	if v.type.code == 5:
# 		global registeredEnums
# 		registered = registeredEnums.get(v.type.name, None)
# 		if registered != None:
# 			return DRegisteredEnumPrinter(v, registered)
# 		elif str(v) == "<incomplete type>":
# 			return DFallbackEnumPrinter(v)
# 	return None

# gdb.printing.register_pretty_printer(gdb.current_objfile(), dlang_enum_printer)
