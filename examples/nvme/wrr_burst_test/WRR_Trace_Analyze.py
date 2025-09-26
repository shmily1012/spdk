'''
Created on Sep 13, 2018

@author: Chi.Zhang
'''
from __future__ import print_function
from __future__ import division
import sys
################################################################
filename = r"WRR_trace.txt"
SQ1_base_adr = 0x274A10000
Increase_step = 0x4000
################################################################
# SQ2_base_adr = SQ1_base_adr + Increase_step
# SQ3_base_adr = SQ2_base_adr + Increase_step
# SQ4_base_adr = SQ3_base_adr + Increase_step
# SQ5_base_adr = SQ4_base_adr + Increase_step
# SQ6_base_adr = SQ5_base_adr + Increase_step
# SQ7_base_adr = SQ6_base_adr + Increase_step
# SQ8_base_adr = SQ7_base_adr + Increase_step
# SQ9_base_adr = SQ8_base_adr + Increase_step
SQ1_base_adr = 0x274a10000
SQ2_base_adr = 0x274c20000
SQ3_base_adr = 0x274c10000
SQ4_base_adr = 0x1a1248000
SQ5_base_adr = 0x275a48000
SQ6_base_adr = 0x275648000
SQ7_base_adr = 0x275448000
SQ8_base_adr = 0x275048000
SQ9_base_adr = 0x274e48000
High = [1, 2, 3]
Middle = [4, 5, 6]
Low = [7, 8, 9]
################################################################
packets_array = list()
if __name__ == '__main__':
    fi = open(filename, 'r')
    buf = fi.readlines()
    fi.close()
    count = 0
    line_id = 0
#     for line in buf:
    while line_id < len(buf):
        # while line_id < 1000:
        if 'Upstream' in buf[line_id] and 'Mem MRd' in buf[line_id] and 'Split Tra' in buf[line_id]:
            # print(buf[line_id])
            Split_ID = 0
            SQ_ID = 0
            number_of_cmds_in_packet = 0
            try:
                start = buf[line_id].index('Split Tra(') + len('Split Tra(')
            except ValueError:
                print(buf[line_id])
                sys.exit(-1)
            end = buf[line_id].index(')', start + 1)
            Split_ID = int(buf[line_id][start:end], 10)
            for i in range(10):
                if 'Address' in buf[line_id + i]:
                    address = 0x0
                    start = buf[line_id +
                                i].index('Address(') + len('Address(')
                    end = buf[line_id + i].index(')', start + 1)
                    if ':' in buf[line_id + i][start:end]:
                        temp = buf[line_id + i][start:end].split(':')
                        high_adr = int(temp[0], 16)
                        low_adr = int(temp[1], 16)
                        address = (high_adr << 32) | low_adr
                    else:
                        address = int(buf[line_id + i][start:end], 16)
                    # if 0xF00000000 & address == 0x400000000:
                    #     print("address1=0x%x" % (address))
                    #     print("address2=0x%x" % (address & 0xFFFFFFFFFFFFC000))

                        # print("0x%x" % SQ1_base_adr)
                        # print("0x%x" % SQ2_base_adr)
                        # print("0x%x" % SQ3_base_adr)
                        # print("0x%x" % SQ4_base_adr)
                        # print("0x%x" % SQ5_base_adr)
                        # print("0x%x" % SQ6_base_adr)
                        # print("0x%x" % SQ7_base_adr)
                        # print("0x%x" % SQ8_base_adr)
                        # print("0x%x" % SQ9_base_adr)
                    break
            # if address < SQ1_base_adr:
            #     SQ_ID = None
            # elif address < SQ1_base_adr+Increase_step:
            #     print("SQ1_base_adr=0x%x" % address)
            #     SQ_ID = 1
            # elif address < SQ2_base_adr+Increase_step:
            #     print("SQ2_base_adr=0x%x" % address)
            #     SQ_ID = 2
            # elif address < SQ3_base_adr+Increase_step:
            #     print("SQ3_base_adr=0x%x" % address)
            #     SQ_ID = 3
            # elif address < SQ4_base_adr+Increase_step:
            #     print("SQ4_base_adr=0x%x" % address)
            #     SQ_ID = 4
            # elif address < SQ5_base_adr+Increase_step:
            #     print("SQ5_base_adr=0x%x" % address)
            #     SQ_ID = 5
            # elif address < SQ6_base_adr+Increase_step:
            #     print("SQ6_base_adr=0x%x" % address)
            #     SQ_ID = 6
            # elif address < SQ7_base_adr+Increase_step:
            #     print("SQ7_base_adr=0x%x" % address)
            #     SQ_ID = 7
            # elif address < SQ8_base_adr+Increase_step:
            #     print("SQ8_base_adr=0x%x" % address)
            #     SQ_ID = 8
            # elif address < SQ9_base_adr+Increase_step:
            #     print("SQ9_base_adr=0x%x" % address)
            #     SQ_ID = 9
            # else:
            #     SQ_ID = None
            if address & 0xFFFFFFFFFFFFF000 == SQ1_base_adr:
                SQ_ID = 1
            elif address & 0xFFFFFFFFFFFFF000 == SQ2_base_adr:
                SQ_ID = 2
            elif address & 0xFFFFFFFFFFFFF000 == SQ3_base_adr:
                SQ_ID = 3
            elif address & 0xFFFFFFFFFFFFF000 == SQ4_base_adr:
                SQ_ID = 4
            elif address & 0xFFFFFFFFFFFFf000 == SQ5_base_adr:
                SQ_ID = 5
            elif address & 0xFFFFFFFFFFFFf000 == SQ6_base_adr:
                SQ_ID = 6
            elif address & 0xFFFFFFFFFFFFF000 == SQ7_base_adr:
                SQ_ID = 7
            elif address & 0xFFFFFFFFFFFFF000 == SQ8_base_adr:
                SQ_ID = 8
            elif address & 0xFFFFFFFFFFFFf000 == SQ9_base_adr:
                SQ_ID = 9
            else:
                SQ_ID = None
#                 print('unknown adrress = 0x{0:x}'.format(address))
#                 sys.exit(-1)
            if SQ_ID is not None:
                print('address = 0x{0:x}'.format(address))
                for i in range(10):
                    #                     print buf[line_id + i]
                    if 'Data(' in buf[line_id + i]:
                        start = buf[line_id + i].index('Data(') + len('Data(')
                        # print('buf[line_id + i]=', buf[line_id + i])
                        end = buf[line_id + i].index('B', start + 1)
                        number_of_cmds_in_packet = int(
                            int(buf[line_id + i][start:end], 10) // 64)
                        break
                for i in range(number_of_cmds_in_packet):
                    packet = {'split_id': Split_ID, 'sq_id': SQ_ID}
                    packets_array.append(packet)
#             print buf[line_id]
#             print buf[line_id + 1]
#             print buf[line_id + 2]
#             print buf[line_id + 3]
#             print buf[line_id + 4]
#             print buf[line_id + 5]
#             print buf[line_id + 6]
#             print buf[line_id + 7]

        line_id += 1
    High_Q = ['High']
    Mid_Q = ['Medium']
    Low_Q = ['Low']

    for packet in packets_array:
        print(packet)
        if packet['sq_id'] in High:
            High_Q.append('{0}'.format(packet['sq_id']))
            Mid_Q.append(' ')
            Low_Q.append(' ')
        elif packet['sq_id'] in Middle:
            High_Q.append(' ')
            Mid_Q.append('{0}'.format(packet['sq_id']))
            Low_Q.append(' ')
        elif packet['sq_id'] in Low:
            High_Q.append(' ')
            Mid_Q.append(' ')
            Low_Q.append('{0}'.format(packet['sq_id']))
    with open(r'results_{0}.csv'.format(filename[:-4]), 'w') as fi:
        # fo.write("split_id,SQID\n")
        # for packet in packets_array:
        #     fo.write("%d,%d\n" % (packet['split_id'], packet['sq_id']))
        fi.write(''.join(item+',' for item in High_Q))
        fi.write('\n')
        fi.write(''.join(item+',' for item in Mid_Q))
        fi.write('\n')
        fi.write(''.join(item+',' for item in Low_Q))
        fi.write('\n')
    print('DONE')
