##
## This file is part of the libsigrokdecode project.
##
## Copyright (C) 2018 James Dervay <jamesdervay@gmail.com>
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, see <http://www.gnu.org/licenses/>.
##

import sigrokdecode as srd

def disabled_enabled(v):
    return ['Disabled', 'Enabled'][v]

def output_power(v):
    return '%+ddBm' % [-4, -1, 2, 5][v]

regs = {
# reg:   name                        offset width parser
    0: [
        ('INT',                           4, 16, None),
        ('Prescaler',                    20,  1, lambda v: ['4/5', '8/9'][v]),
        ('AutoCal',                      21,  1, disabled_enabled)
    ],
    1: [
        ('FRAC1',                         4, 24, None)
    ],
    2: [
        ('MOD2',                          4, 14, None),
        ('FRAC2',                        18, 14, None)
    ],
    3: [
        ('Phase',                        4,  24, None),
        ('Phase Adjust',                 28,  1, disabled_enabled),
        ('Phase Resync',                 29,  1, disabled_enabled),
        ('SD Load Reset',                30,  1, disabled_enabled)
    ],
    4: [
        ('Counter Reset',                 4,  1, disabled_enabled),
        ('CP Three State',                5,  1, disabled_enabled),
        ('Power Down',                    6,  1, disabled_enabled),
        ('PD Polarity',                   7,  1, lambda v: ['Negative', 'Positive'][v]),
        ('MUX Logic',                     8,  1, lambda v: ['1.8V', '3.3V'][v]),
        ('REF Mode',                      9,  1, lambda v: ['Single', 'Diff'][v]),
        ('Current Setting (mA)',         10,  4, lambda v: [
            '0.31', '0.63', '0.94', '1.25', '1.56', '1.88', '2.19', '2.50',
            '2.81', '3.13', '3.44', '3.75', '4.06', '4.38', '4.69', '5.00'][v]),
        ('10 Bit R Counter',             15, 10, None),
        ('Reference Divide By 2',        25,  1, disabled_enabled),
        ('Reference Doubler',            26,  1, disabled_enabled),
        ('MUX Out',                      27,  3, lambda v: [
            'Three- State Output', 'DVdd', 'DGnd', 'R Divider Output',
            'N Divider Output', 'Analog Lock Detect', 'Digital Lock Detect'][v])
    ],
    5: [
        #('Reserved',                     4, 28, None)
    ],
    6: [
        ('RF Output Power',              4,  2, output_power),
        ('RF Out A',                     6,  1, disabled_enabled),
        ('RF Out B',                    10,  1, disabled_enabled),
        ('Mute Till Lock Detect',       11,  1, disabled_enabled),
        ('Charge Pump Bleed Current',   13,  8, None),
        ('RF Divider Select',           21,  3, lambda v: [
            '1', '2', '4', '8', '16', '32', '64'][v]),
        ('Feedback Select',             24,  1, lambda v: ['Divided', 'Fundamental'][v]),
        ('Negative Bleed',              29,  1, disabled_enabled),
        ('Gated Bleed',                 30,  1, disabled_enabled)
    ],
    7: [
        ('Lock Detect Mode',             4,  1, lambda v: ['FRAC-N', 'INT-N'][v]),
        ('FRAC-N LD Precision (ns)',     5,  2, lambda v: ['5', '6', '8', '12'][v]),
        ('Loss of Lock Mode',            7,  1, disabled_enabled),
        ('LD Cycle Count',               8,  2, lambda v: [
            '1024', '2048', '4096', '8192'][v]),
        ('LE Sync',                     25,  1, disabled_enabled)
    ],
    8: [
        #('Reserved',                     4,  28, None)
    ],
    9: [
        ('Synth Lock Timeout',           4,  5, None),
        ('Auto Level Timeout',           9,  5, None),
        ('Timeout',                     14, 10, None),
        ('VCO Band Division',           24,  8, None)
    ],
    10: [
        ('ADC Enable',                   4,  1, disabled_enabled),
        ('ADC Conversion',               5,  1, disabled_enabled),
        ('ADC Clock Divider',            6,  8, None)
    ],
    11: [
        #('Reserved',                     4, 28, None)
    ],
    12: [
        ('Phase Resync Clock Divider',  16, 16, None)
    ]
}

ANN_REG = 0

class Decoder(srd.Decoder):
    api_version = 3
    id = 'adf5355'
    name = 'ADF5355'
    longname = 'Analog Devices ADF5355'
    desc = 'Microwave Wideband Synthesizer with Integrated VCO.'
    license = 'gplv3+'
    inputs = ['spi']
    outputs = ['adf5355']
    annotations = (
        # Sent from the host to the chip.
        ('register', 'Register written to the device'),
    )
    annotation_rows = (
        ('registers', 'Register writes', (ANN_REG,)),
    )

    def __init__(self):
        self.reset()

    def reset(self):
        self.bits = []

    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)

    def decode_bits(self, offset, width):
        return (sum([(1 << i) if self.bits[offset + i][0] else 0 for i in range(width)]),
            (self.bits[offset + width - 1][1], self.bits[offset][2]))

    def decode_field(self, name, offset, width, parser):
        val, pos = self.decode_bits(offset, width)
        self.put(pos[0], pos[1], self.out_ann, [ANN_REG,
            ['%s: %s' % (name, parser(val) if parser else str(val))]])
        return val

    def decode(self, ss, es, data):

        ptype, data1, data2 = data

        if ptype == 'CS-CHANGE':
            if data1 == 1:
                if len(self.bits) == 32:
                    reg_value, reg_pos = self.decode_bits(0, 4)
                    self.put(reg_pos[0], reg_pos[1], self.out_ann, [ANN_REG,
                        ['Register: %d' % reg_value, 'Reg: %d' % reg_value,
                         '[%d]' % reg_value]])
                    if reg_value < len(regs):
                        field_descs = regs[reg_value]
                        for field_desc in field_descs:
                            field = self.decode_field(*field_desc)
                self.bits = []
        if ptype == 'BITS':
            self.bits = data1 + self.bits
