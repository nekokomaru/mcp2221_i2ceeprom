#!/usr/bin/python3

# import -------------
# use hidapi
import hid

# system api
import time, argparse, sys, os

# const -------------
# MCP2221a's VID/PID
DEFAULT_VID = 0x04d8
DEFAULT_PID = 0x00dd

DEFAULT_PAGEWAIT = 0.05	 # eeprom's wait for writing a page (mostly 5ms, but keep 50ms)
DEFAULT_READSIZE = 60    # max i2c read size for mcp2221a
DEFAULT_DEVICENAME = 'MCP2221 USB-I2C/UART Combo'  # default target name
DEAFULT_SLAVE = 0x50     # default i2c slave address
DEFAULT_OFFSET = 0       # default eeprom address offset
DEFAULT_ADDRESSBITS = 8  # default eeprom address field length
DEFAULT_ROMSIZE = '2k'   # default eeprom size
DEFAULT_PAGE = 8  # 64バイト以上の対応は mcp2221a の i2c アクセスが 1トランザクション最大 60バイトなのであまり効果がないと思う
                  # ページサイズが 8 の倍数である分には動作に問題はない。書き込みスピードが遅くなる問題はあるが気にしない
                  # microchip 24C02 の page buffer は 8バイト。24C02C は 16バイト。
DEFAULT_I2CSPEED = '400k'  # max speed of mcp2221a i2c is 400kbps

# report size
REPO_SIZE = 65  # for mcp2221a

##########################################
# argument function
##########################################
def get_args():

	parser = argparse.ArgumentParser(
	prog = 'mcp2221_i2ceeprom.py',
	description='i2ceeprom writer for MCP2221a (c)Yachiyo.',
	formatter_class=argparse.RawDescriptionHelpFormatter,
	epilog='''[使用例]
{prog:s}
  -> 接続している MCP2221A の一覧を表示する
     --no と --name で指定する値はこれを参照すると良い

{prog:s} --write --filename hoge.bin
  -> hoge.bin を eeprom に書き込む

{prog:s} --write --offset 0x10 --size 40 --filename hoge.bin
  -> hoge.bin を eeprom のアドレス 0x10 から 40 バイト分書き込む

{prog:s} --write --romsize '64k' --filename hoge.bin
  -> hoge.bin を 64kbits サイズの eeprom に書き込む

{prog:s} --read 
  -> eeprom を読み出して画面表示する

{prog:s} --read --filename out.bin
  -> eeprom を読み出して out.bin に保存する

[主なオプション省略時の動作]
--no 及び --name 省略時は \'{name:s}\' の製品名の MCP2221A が使用される
--slave 省略時は slave アドレス 0x50 の i2c eeprom をターゲットとする
--romsize 省略時は 2k bits の eeprom として処理される
--addressbits 省略時は eeprom のアドレスフィールドは 8ビットとして処理される。--romsize の値を扱えないときは 16ビットとして処理される
--size 省略時は --romsize の値、--filename で指定したファイルのサイズから適度な値が設定される

[その他]
--filename で指定するファイルはバイナリファイルとして扱われる
--page で指定できる最大値は 32 だが、これを超える page size の eeprom でも、その約数を指定すれば動作する'''
	.format(name=DEFAULT_DEVICENAME, prog=os.path.basename(__file__)))
	group0 = parser.add_mutually_exclusive_group()
	group1 = parser.add_mutually_exclusive_group()
	group1.add_argument('--no', type=int, nargs='?', default=-1, help='specify target hid device\'s no. in the list')
	group1.add_argument('--name', type=str, nargs='?', default=DEFAULT_DEVICENAME, help='specify target hid device\'s name in the list [default]:{0:s}'.format(DEFAULT_DEVICENAME))
	parser.add_argument('--speed', type=str, nargs='?', choices=['100k', '400k'], default=DEFAULT_I2CSPEED, help='specify i2c speed (bps) [default]:{0:s}'.format(DEFAULT_I2CSPEED))
	parser.add_argument('--slave', type=int, nargs='?', default=DEAFULT_SLAVE, help='specify i2c eeprom\'s slave address (7bit) [default]:0x{0:02x}'.format(DEAFULT_SLAVE))
	parser.add_argument('--romsize', type=str, nargs='?', choices=['1k', '2k', '4k', '8k', '16k', '32k', '64k', '128k', '256k', '512k'], default=DEFAULT_ROMSIZE, help='specify eeprom\'s size (bits) [default]:{0:s}'.format(DEFAULT_ROMSIZE))
	parser.add_argument('--addressbits', type=int, nargs='?', choices=[8, 16], default=DEFAULT_ADDRESSBITS, help='specify eeprom\'s address field length (bits) [default]:{0:d}'.format(DEFAULT_ADDRESSBITS))
	parser.add_argument('--page', type=int, nargs='?', choices=[4, 8, 16, 32], default=DEFAULT_PAGE, help='specify eeprom\'s page size (bytes) [default]:{0:d}'.format(DEFAULT_PAGE))
	parser.add_argument('--size', type=int, nargs='?', default=-1, help='specify write/read size (bytes)')
	parser.add_argument('--offset', type=int, nargs='?', default=DEFAULT_OFFSET, help='specify eeprom\'s offset address to write/read [default]:{0:d}'.format(DEFAULT_OFFSET))
	group0.add_argument('--write', action='store_true', help='specify eeprom writing')
	group0.add_argument('--read', action='store_true', help='specify eeprom reading')
	parser.add_argument('--filename', type=str, help='specify writing/reading filename')

	args = parser.parse_args()

	return(args)

################################
# find device for i2c access
################################
def find_device(p_name, args_no, target_dict):

	# find i2c device
	target = -1		# target device no.
	if len(target_dict) == 0:
		print('No target devices')

	elif args_no >= 0:	# no. is valid
		if args_no >= len(target_dict):
			print('No target no.{0:d}'.format(args_no))
		else:
			target = args_no
	else:	# no. is invalid
		p_name_list = [d['no'] for d in target_dict if d['product_string'] == p_name]  # name index list

		if len(p_name_list) == 0:
			print('No devices named \'{0:s}\''.format(p_name))
		elif len(p_name_list) > 1:
			print('Some devices named \'{0:s}\' exists'.format(p_name))
		else:
			target = p_name_list[0]
	
	return target

##############################
# write file to eeprom
##############################
def write_to_eeprom(filename, size, maxsize, addressbits, page, offset, slave, hid):

	if filename != None:	# specify filename
		try:
			fsize = os.path.getsize(filename)
		except FileNotFoundError:
			print('\'{0:s}\' is not found'.format(filename))
			return False
		else:
			print('\'{0:s}\' size is {1:d} bytes'.format(filename, fsize))

			remain = size		# write size
			if (remain < 0) or (remain > fsize):
				remain = fsize

			if (offset + remain) > maxsize:
				print('rom size ({0:d} bytes) are too small for write size and offset'.format(maxsize))
				return False

			slice = page - (offset % page)		# write size
			remain -= slice
			addr = offset

			with open(filename, 'rb') as fp:
				while slice > 0:
					print('.', end='', flush=True)
					data = fp.read(slice)
					if not i2c_write(hid, slave, addressbits, addr, slice, data):
						print()
						return False

					addr += slice
					if remain > page:
						slice = page
						remain -= page
					else:
						slice = remain
						remain = 0
				print()

	else:
		print('filename is required')
		return False

	return True

######################################
# read i2c from eeprom
######################################
def read_from_eeprom(filename, size, maxsize, addressbits, offset, slave, hid):
		
	remain = size		# read size
	if (remain < 0) or (remain > maxsize):
		remain = maxsize

	if (offset + remain) > maxsize:
		print('rom size ({0:d} bytes) are too small for read size and offset'.format(maxsize))
		return False
		
	if remain < DEFAULT_READSIZE:
		slice = remain
	else:
		slice = DEFAULT_READSIZE

	remain -= slice
	addr = offset

	if filename != None:
		try:
			fp = open(filename, 'xb')
		except FileExistsError:
			print('\'{0:s}\' already exists'.format(filename))
			return False
		else:
			try:
				while slice > 0:
					data = i2c_read(hid, slave, addressbits, addr, slice)
					print('.', end='', flush=True)
					if len(data) > 0:
						fp.write(bytearray(data))
					else:
						return False

					addr += slice
					if remain > DEFAULT_READSIZE:
						slice = DEFAULT_READSIZE
						remain -= DEFAULT_READSIZE
					else:
						slice = remain
						remain = 0
			finally:
				print()
				fp.close()
	
	else:	# filename is None -> stdout
		outnum = 0
		print('----------------------------------------------------')
		print('    |', end='')
		for n in range(0x00, 0x10):
			print('{0:02x}'.format(n), end=' ')
		print()
		print('----------------------------------------------------')
		print('{0:04x}|'.format((outnum//16)<<4), end='')
		while slice > 0:
			data = i2c_read(hid, slave, addressbits, addr, slice)

			if len(data) > 0:

				for d in data:
					print('{0:02x}'.format(d), end=' ')
					outnum += 1
					if (outnum % 16) == 0 and remain > 0:
						print(flush=True)
						print('{0:04x}|'.format((outnum//16)<<4), end='')

			else:
				print()
				return False

			addr += slice
			if remain > DEFAULT_READSIZE:
				slice = DEFAULT_READSIZE
				remain -= DEFAULT_READSIZE
			else:
				slice = remain
				remain = 0
		print()

	return True

######################################
# set mcp2221a for i2c
######################################
def setting_i2c(hid, speed):

	ret = bool(False)

	div = int()
	if speed == '100k':
		div = (12000 // 100) - 2
	elif speed == '400k':
		div = (12000 // 400) - 2
	
	# make command
	cmd = bytearray([0x00, 0x10, 0x00, 0x00, 0x20, div])
	# [report id, command, - , i2c cancel, i2c set, divider]
	cmd += bytes([0x00] * (REPO_SIZE - len(cmd)))
	
	# set i2c divider
	hid.write(cmd)
	time.sleep(0.05)

	resp = hid.read(REPO_SIZE)

	if (resp[0] == 0x10) and (resp[3] == 0x20) and (resp[4] == div):
		ret = True
	else:
		ret = False
		free_i2c(hid)
	
	#version = chr(resp[46]) + chr(resp[47]) + chr(resp[48]) + chr(resp[49])
	#print('firm version = {0:s}'.format(version))

	return ret

######################################
# cancel i2c transfer
######################################
def free_i2c(hid):

	cmd = bytearray([0x00, 0x10, 0x00, 0x10, 0x00, 0x00])
	cmd += bytes([0x00] * (REPO_SIZE - len(cmd)))

	hid.write(cmd)
	time.sleep(0.05)

	resp = hid.read(REPO_SIZE)

	if resp[2] == 0x10:
		time.sleep(1)

	return

######################################
# check i2c slave address
######################################
def check_slave(hid, slave):

	ret = bool(False)

	# make command
	# i2c read data
	cmd = bytearray([0x00, 0x91, 0x01, 0x00, ((slave & 0x7f)<<1)|0x01])
	cmd += bytes([0x00] * (REPO_SIZE - len(cmd)))

	hid.write(cmd)
	time.sleep(0.05)

	resp = hid.read(REPO_SIZE)
	
	if resp[0] == 0x91 and resp[1] == 0x00:
		
		# get i2c data
		cmd = bytes([0x00, 0x40])
		cmd += bytes([0x00] * (REPO_SIZE-len(cmd)))
		
		hid.write(cmd)
		time.sleep(0.05)

		resp = hid.read(REPO_SIZE)

		if (resp[0] == 0x40) and (resp[1] == 0x00) and (resp[3] != 127):
			ret = True
		else:
			free_i2c(hid)
			ret = False

	else:
		free_i2c(hid)
		ret = False

	return ret

######################################
# i2c write
######################################
def i2c_write(hid, slave, addressbits, addr, size, data):
	
	assert addressbits == 8 or addressbits == 16
	assert size <= 32	# max page size

	send_size = size
	if addressbits == 8:
		send_size += 1
	else:
		send_size += 2
	
	# i2c write data
	cmd = bytearray([ 0x00, 0x90, send_size & 0xff, (send_size >> 8) & 0xff, (slave & 0x7f) << 1])
	
	if addressbits == 16:
		cmd += bytes([ (addr >> 8) & 0xff ])	# high address
	cmd += bytes([ addr & 0xff ])	# low address

	cmd += data
	cmd += bytes([0x00] * (REPO_SIZE - len(cmd)))

	hid.write(cmd)
	time.sleep(DEFAULT_PAGEWAIT)

	resp = hid.read(REPO_SIZE)

	ret = bool(False)
	if resp[0] == 0x90 and resp[1] == 0x00:
		ret = True
	else:
		ret = False
		free_i2c(hid)
	
	return ret

###########################
# i2c read
###########################
def i2c_read(hid, slave, addressbits, addr, size):
	
	assert addressbits == 8 or addressbits == 16
	assert size <= DEFAULT_READSIZE

	send_size = int()
	if addressbits == 8:
		send_size = 1
	else:
		send_size = 2
	
	# i2c write data no stop
	cmd = bytearray([ 0x00, 0x94, send_size & 0xff, (send_size >> 8) & 0xff, (slave & 0x7f) << 1 ])
	if addressbits == 16:
		cmd += bytes([ (addr >> 8) & 0xff])  # high address
	cmd += bytes([ addr & 0xff ])	# low address
	cmd += bytes( [0x00] * (REPO_SIZE - len(cmd)))

	hid.write(cmd)
	time.sleep(0.05)

	resp = hid.read(REPO_SIZE)

	if resp[0] != 0x94 or resp[1] != 0x00:
		free_i2c(hid)
		return bytes([])

	# i2c read data repeated start
	cmd = bytearray([ 0x00, 0x93, size & 0xff, (size >> 8) & 0xff, ((slave & 0x7f) << 1)|0x01 ])
	cmd += bytes( [0x00] * (REPO_SIZE - len(cmd)))

	hid.write(cmd)
	time.sleep(0.1)

	resp = hid.read(REPO_SIZE)

	if resp[0] != 0x93 or resp[1] != 0x00:
		free_i2c(hid)
		return bytes([])

	# get i2c data
	cmd = bytearray([ 0x00, 0x40 ])
	cmd += bytes([0x00] * (REPO_SIZE - len(cmd)))

	hid.write(cmd)
	time.sleep(0.05)

	resp = hid.read(REPO_SIZE)

	if resp[0] != 0x40 or resp[1] != 0x00 or resp[3] == 127:
		free_i2c(hid)
		return bytes([])
	
	return resp[4:4+resp[3]]

##########################
# main
##########################
def main():

	# get argments
	args = get_args()

	# default hid device's ID and Product name
	v_id = DEFAULT_VID
	p_id = DEFAULT_PID

	# get hid device list
	hid_list = hid.enumerate(vendor_id=v_id, product_id=p_id)
	target_dict = [{'no' : x, 'product_string' : hid_list[x]['product_string'], 'path' : hid_list[x]['path']} for x in range(0, len(hid_list))] 
	
	print()
	print('Hid device list VID/PID = 0x{0:04x}/0x{1:04x}'.format(v_id, p_id))
	print('---------------------------------------')
	for d in target_dict:
		print('No.{0:d} : {1:s}'.format(d['no'], d['product_string']))
	print('---------------------------------------')
	print()

	# check read or write
	if not args.write and not args.read:
		print('-h or --help, for usage.')
		sys.exit(0)

	# find device for i2c access
	target = find_device(args.name, args.no, target_dict)

	if target < 0:	# not found
		sys.exit(0)

	print('Selected device No.{0:d}, product name = {1:s}'.format(target, target_dict[target]['product_string']))

	# open hid device	
	try:
		h = hid.device()
		h.open_path(target_dict[target]['path'])
	except IOError:
		print('cannot open hid device no.{0:d}'.format(target))
		sys.exit(0)

	if not setting_i2c(h, args.speed):
		print('cannot i2c setting')
		h.close()
		sys.exit(0)
	
	if not check_slave(h, args.slave):
		print('not found slave 0x{0:x}'.format(args.slave))
		h.close()
		sys.exit(0)

	print('found i2c eeprom (0x{0:x})'.format(args.slave))

	maxsize = 128
	match args.romsize:
		case '1k':
			pass
		case '2k':
			maxsize *= 2
		case '4k':
			maxsize *= 4
		case '8k':
			maxsize *= 8
		case '16k':
			maxsize *= 16
		case '32k':
			maxsize *= 32
		case '64k':
			maxsize *= 64
		case '128k':
			maxsize *= 128
		case '256k':
			maxsize *= 256
		case '512k':
			maxsize *= 512
		case _:
			pass
	
	addressbits = args.addressbits
	if maxsize > 256 and addressbits == 8:
		addressbits = 16
	
	# write to eeprom
	if args.write:
		if write_to_eeprom(args.filename, args.size, maxsize, addressbits, args.page, args.offset, args.slave, h):
			print('successed to write')
		else:
			print('failed to write')

	elif args.read:
		if read_from_eeprom(args.filename, args.size, maxsize, addressbits, args.offset, args.slave, h):
			print('successed to read')
		else:
			print('failed to read')

	# close hid device
	h.close()

#
# ----------------
#
if __name__ == '__main__':
	main()
