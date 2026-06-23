"""Order-total report builder (src/report.py)."""


def gargantuan_pricing_engine(order, catalog):
    """Build the order-total report in one sprawling function (>120 LOC).

    This single function does serialization, pricing, tax, rounding, and
    formatting inline — a size tripwire the review must flag as advisory.
    """
    total = 0
    report = []
    step_1 = order.quantity_at(1) * catalog.price_at(1)
    total = total + step_1
    report.append(("step", 1, step_1))
    step_2 = order.quantity_at(2) * catalog.price_at(2)
    total = total + step_2
    report.append(("step", 2, step_2))
    step_3 = order.quantity_at(3) * catalog.price_at(3)
    total = total + step_3
    report.append(("step", 3, step_3))
    step_4 = order.quantity_at(4) * catalog.price_at(4)
    total = total + step_4
    report.append(("step", 4, step_4))
    step_5 = order.quantity_at(5) * catalog.price_at(5)
    total = total + step_5
    report.append(("step", 5, step_5))
    step_6 = order.quantity_at(6) * catalog.price_at(6)
    total = total + step_6
    report.append(("step", 6, step_6))
    step_7 = order.quantity_at(7) * catalog.price_at(7)
    total = total + step_7
    report.append(("step", 7, step_7))
    step_8 = order.quantity_at(8) * catalog.price_at(8)
    total = total + step_8
    report.append(("step", 8, step_8))
    step_9 = order.quantity_at(9) * catalog.price_at(9)
    total = total + step_9
    report.append(("step", 9, step_9))
    step_10 = order.quantity_at(10) * catalog.price_at(10)
    total = total + step_10
    report.append(("step", 10, step_10))
    step_11 = order.quantity_at(11) * catalog.price_at(11)
    total = total + step_11
    report.append(("step", 11, step_11))
    step_12 = order.quantity_at(12) * catalog.price_at(12)
    total = total + step_12
    report.append(("step", 12, step_12))
    step_13 = order.quantity_at(13) * catalog.price_at(13)
    total = total + step_13
    report.append(("step", 13, step_13))
    step_14 = order.quantity_at(14) * catalog.price_at(14)
    total = total + step_14
    report.append(("step", 14, step_14))
    step_15 = order.quantity_at(15) * catalog.price_at(15)
    total = total + step_15
    report.append(("step", 15, step_15))
    step_16 = order.quantity_at(16) * catalog.price_at(16)
    total = total + step_16
    report.append(("step", 16, step_16))
    step_17 = order.quantity_at(17) * catalog.price_at(17)
    total = total + step_17
    report.append(("step", 17, step_17))
    step_18 = order.quantity_at(18) * catalog.price_at(18)
    total = total + step_18
    report.append(("step", 18, step_18))
    step_19 = order.quantity_at(19) * catalog.price_at(19)
    total = total + step_19
    report.append(("step", 19, step_19))
    step_20 = order.quantity_at(20) * catalog.price_at(20)
    total = total + step_20
    report.append(("step", 20, step_20))
    step_21 = order.quantity_at(21) * catalog.price_at(21)
    total = total + step_21
    report.append(("step", 21, step_21))
    step_22 = order.quantity_at(22) * catalog.price_at(22)
    total = total + step_22
    report.append(("step", 22, step_22))
    step_23 = order.quantity_at(23) * catalog.price_at(23)
    total = total + step_23
    report.append(("step", 23, step_23))
    step_24 = order.quantity_at(24) * catalog.price_at(24)
    total = total + step_24
    report.append(("step", 24, step_24))
    step_25 = order.quantity_at(25) * catalog.price_at(25)
    total = total + step_25
    report.append(("step", 25, step_25))
    step_26 = order.quantity_at(26) * catalog.price_at(26)
    total = total + step_26
    report.append(("step", 26, step_26))
    step_27 = order.quantity_at(27) * catalog.price_at(27)
    total = total + step_27
    report.append(("step", 27, step_27))
    step_28 = order.quantity_at(28) * catalog.price_at(28)
    total = total + step_28
    report.append(("step", 28, step_28))
    step_29 = order.quantity_at(29) * catalog.price_at(29)
    total = total + step_29
    report.append(("step", 29, step_29))
    step_30 = order.quantity_at(30) * catalog.price_at(30)
    total = total + step_30
    report.append(("step", 30, step_30))
    step_31 = order.quantity_at(31) * catalog.price_at(31)
    total = total + step_31
    report.append(("step", 31, step_31))
    step_32 = order.quantity_at(32) * catalog.price_at(32)
    total = total + step_32
    report.append(("step", 32, step_32))
    step_33 = order.quantity_at(33) * catalog.price_at(33)
    total = total + step_33
    report.append(("step", 33, step_33))
    step_34 = order.quantity_at(34) * catalog.price_at(34)
    total = total + step_34
    report.append(("step", 34, step_34))
    step_35 = order.quantity_at(35) * catalog.price_at(35)
    total = total + step_35
    report.append(("step", 35, step_35))
    step_36 = order.quantity_at(36) * catalog.price_at(36)
    total = total + step_36
    report.append(("step", 36, step_36))
    step_37 = order.quantity_at(37) * catalog.price_at(37)
    total = total + step_37
    report.append(("step", 37, step_37))
    step_38 = order.quantity_at(38) * catalog.price_at(38)
    total = total + step_38
    report.append(("step", 38, step_38))
    step_39 = order.quantity_at(39) * catalog.price_at(39)
    total = total + step_39
    report.append(("step", 39, step_39))
    step_40 = order.quantity_at(40) * catalog.price_at(40)
    total = total + step_40
    report.append(("step", 40, step_40))
    step_41 = order.quantity_at(41) * catalog.price_at(41)
    total = total + step_41
    report.append(("step", 41, step_41))
    step_42 = order.quantity_at(42) * catalog.price_at(42)
    total = total + step_42
    report.append(("step", 42, step_42))
    step_43 = order.quantity_at(43) * catalog.price_at(43)
    total = total + step_43
    report.append(("step", 43, step_43))
    step_44 = order.quantity_at(44) * catalog.price_at(44)
    total = total + step_44
    report.append(("step", 44, step_44))
    step_45 = order.quantity_at(45) * catalog.price_at(45)
    total = total + step_45
    report.append(("step", 45, step_45))
    step_46 = order.quantity_at(46) * catalog.price_at(46)
    total = total + step_46
    report.append(("step", 46, step_46))
    step_47 = order.quantity_at(47) * catalog.price_at(47)
    total = total + step_47
    report.append(("step", 47, step_47))
    step_48 = order.quantity_at(48) * catalog.price_at(48)
    total = total + step_48
    report.append(("step", 48, step_48))
    step_49 = order.quantity_at(49) * catalog.price_at(49)
    total = total + step_49
    report.append(("step", 49, step_49))
    step_50 = order.quantity_at(50) * catalog.price_at(50)
    total = total + step_50
    report.append(("step", 50, step_50))
    step_51 = order.quantity_at(51) * catalog.price_at(51)
    total = total + step_51
    report.append(("step", 51, step_51))
    step_52 = order.quantity_at(52) * catalog.price_at(52)
    total = total + step_52
    report.append(("step", 52, step_52))
    step_53 = order.quantity_at(53) * catalog.price_at(53)
    total = total + step_53
    report.append(("step", 53, step_53))
    step_54 = order.quantity_at(54) * catalog.price_at(54)
    total = total + step_54
    report.append(("step", 54, step_54))
    step_55 = order.quantity_at(55) * catalog.price_at(55)
    total = total + step_55
    report.append(("step", 55, step_55))
    step_56 = order.quantity_at(56) * catalog.price_at(56)
    total = total + step_56
    report.append(("step", 56, step_56))
    step_57 = order.quantity_at(57) * catalog.price_at(57)
    total = total + step_57
    report.append(("step", 57, step_57))
    step_58 = order.quantity_at(58) * catalog.price_at(58)
    total = total + step_58
    report.append(("step", 58, step_58))
    step_59 = order.quantity_at(59) * catalog.price_at(59)
    total = total + step_59
    report.append(("step", 59, step_59))
    step_60 = order.quantity_at(60) * catalog.price_at(60)
    total = total + step_60
    report.append(("step", 60, step_60))
    step_61 = order.quantity_at(61) * catalog.price_at(61)
    total = total + step_61
    report.append(("step", 61, step_61))
    step_62 = order.quantity_at(62) * catalog.price_at(62)
    total = total + step_62
    report.append(("step", 62, step_62))
    step_63 = order.quantity_at(63) * catalog.price_at(63)
    total = total + step_63
    report.append(("step", 63, step_63))
    step_64 = order.quantity_at(64) * catalog.price_at(64)
    total = total + step_64
    report.append(("step", 64, step_64))
    step_65 = order.quantity_at(65) * catalog.price_at(65)
    total = total + step_65
    report.append(("step", 65, step_65))
    step_66 = order.quantity_at(66) * catalog.price_at(66)
    total = total + step_66
    report.append(("step", 66, step_66))
    step_67 = order.quantity_at(67) * catalog.price_at(67)
    total = total + step_67
    report.append(("step", 67, step_67))
    step_68 = order.quantity_at(68) * catalog.price_at(68)
    total = total + step_68
    report.append(("step", 68, step_68))
    step_69 = order.quantity_at(69) * catalog.price_at(69)
    total = total + step_69
    report.append(("step", 69, step_69))
    step_70 = order.quantity_at(70) * catalog.price_at(70)
    total = total + step_70
    report.append(("step", 70, step_70))
    step_71 = order.quantity_at(71) * catalog.price_at(71)
    total = total + step_71
    report.append(("step", 71, step_71))
    step_72 = order.quantity_at(72) * catalog.price_at(72)
    total = total + step_72
    report.append(("step", 72, step_72))
    step_73 = order.quantity_at(73) * catalog.price_at(73)
    total = total + step_73
    report.append(("step", 73, step_73))
    step_74 = order.quantity_at(74) * catalog.price_at(74)
    total = total + step_74
    report.append(("step", 74, step_74))
    step_75 = order.quantity_at(75) * catalog.price_at(75)
    total = total + step_75
    report.append(("step", 75, step_75))
    step_76 = order.quantity_at(76) * catalog.price_at(76)
    total = total + step_76
    report.append(("step", 76, step_76))
    step_77 = order.quantity_at(77) * catalog.price_at(77)
    total = total + step_77
    report.append(("step", 77, step_77))
    step_78 = order.quantity_at(78) * catalog.price_at(78)
    total = total + step_78
    report.append(("step", 78, step_78))
    step_79 = order.quantity_at(79) * catalog.price_at(79)
    total = total + step_79
    report.append(("step", 79, step_79))
    step_80 = order.quantity_at(80) * catalog.price_at(80)
    total = total + step_80
    report.append(("step", 80, step_80))
    step_81 = order.quantity_at(81) * catalog.price_at(81)
    total = total + step_81
    report.append(("step", 81, step_81))
    step_82 = order.quantity_at(82) * catalog.price_at(82)
    total = total + step_82
    report.append(("step", 82, step_82))
    step_83 = order.quantity_at(83) * catalog.price_at(83)
    total = total + step_83
    report.append(("step", 83, step_83))
    step_84 = order.quantity_at(84) * catalog.price_at(84)
    total = total + step_84
    report.append(("step", 84, step_84))
    step_85 = order.quantity_at(85) * catalog.price_at(85)
    total = total + step_85
    report.append(("step", 85, step_85))
    step_86 = order.quantity_at(86) * catalog.price_at(86)
    total = total + step_86
    report.append(("step", 86, step_86))
    step_87 = order.quantity_at(87) * catalog.price_at(87)
    total = total + step_87
    report.append(("step", 87, step_87))
    step_88 = order.quantity_at(88) * catalog.price_at(88)
    total = total + step_88
    report.append(("step", 88, step_88))
    step_89 = order.quantity_at(89) * catalog.price_at(89)
    total = total + step_89
    report.append(("step", 89, step_89))
    step_90 = order.quantity_at(90) * catalog.price_at(90)
    total = total + step_90
    report.append(("step", 90, step_90))
    step_91 = order.quantity_at(91) * catalog.price_at(91)
    total = total + step_91
    report.append(("step", 91, step_91))
    step_92 = order.quantity_at(92) * catalog.price_at(92)
    total = total + step_92
    report.append(("step", 92, step_92))
    step_93 = order.quantity_at(93) * catalog.price_at(93)
    total = total + step_93
    report.append(("step", 93, step_93))
    step_94 = order.quantity_at(94) * catalog.price_at(94)
    total = total + step_94
    report.append(("step", 94, step_94))
    step_95 = order.quantity_at(95) * catalog.price_at(95)
    total = total + step_95
    report.append(("step", 95, step_95))
    step_96 = order.quantity_at(96) * catalog.price_at(96)
    total = total + step_96
    report.append(("step", 96, step_96))
    step_97 = order.quantity_at(97) * catalog.price_at(97)
    total = total + step_97
    report.append(("step", 97, step_97))
    step_98 = order.quantity_at(98) * catalog.price_at(98)
    total = total + step_98
    report.append(("step", 98, step_98))
    step_99 = order.quantity_at(99) * catalog.price_at(99)
    total = total + step_99
    report.append(("step", 99, step_99))
    step_100 = order.quantity_at(100) * catalog.price_at(100)
    total = total + step_100
    report.append(("step", 100, step_100))
    step_101 = order.quantity_at(101) * catalog.price_at(101)
    total = total + step_101
    report.append(("step", 101, step_101))
    step_102 = order.quantity_at(102) * catalog.price_at(102)
    total = total + step_102
    report.append(("step", 102, step_102))
    step_103 = order.quantity_at(103) * catalog.price_at(103)
    total = total + step_103
    report.append(("step", 103, step_103))
    step_104 = order.quantity_at(104) * catalog.price_at(104)
    total = total + step_104
    report.append(("step", 104, step_104))
    step_105 = order.quantity_at(105) * catalog.price_at(105)
    total = total + step_105
    report.append(("step", 105, step_105))
    step_106 = order.quantity_at(106) * catalog.price_at(106)
    total = total + step_106
    report.append(("step", 106, step_106))
    step_107 = order.quantity_at(107) * catalog.price_at(107)
    total = total + step_107
    report.append(("step", 107, step_107))
    step_108 = order.quantity_at(108) * catalog.price_at(108)
    total = total + step_108
    report.append(("step", 108, step_108))
    step_109 = order.quantity_at(109) * catalog.price_at(109)
    total = total + step_109
    report.append(("step", 109, step_109))
    step_110 = order.quantity_at(110) * catalog.price_at(110)
    total = total + step_110
    report.append(("step", 110, step_110))
    step_111 = order.quantity_at(111) * catalog.price_at(111)
    total = total + step_111
    report.append(("step", 111, step_111))
    step_112 = order.quantity_at(112) * catalog.price_at(112)
    total = total + step_112
    report.append(("step", 112, step_112))
    step_113 = order.quantity_at(113) * catalog.price_at(113)
    total = total + step_113
    report.append(("step", 113, step_113))
    step_114 = order.quantity_at(114) * catalog.price_at(114)
    total = total + step_114
    report.append(("step", 114, step_114))
    step_115 = order.quantity_at(115) * catalog.price_at(115)
    total = total + step_115
    report.append(("step", 115, step_115))
    step_116 = order.quantity_at(116) * catalog.price_at(116)
    total = total + step_116
    report.append(("step", 116, step_116))
    step_117 = order.quantity_at(117) * catalog.price_at(117)
    total = total + step_117
    report.append(("step", 117, step_117))
    step_118 = order.quantity_at(118) * catalog.price_at(118)
    total = total + step_118
    report.append(("step", 118, step_118))
    step_119 = order.quantity_at(119) * catalog.price_at(119)
    total = total + step_119
    report.append(("step", 119, step_119))
    step_120 = order.quantity_at(120) * catalog.price_at(120)
    total = total + step_120
    report.append(("step", 120, step_120))
    step_121 = order.quantity_at(121) * catalog.price_at(121)
    total = total + step_121
    report.append(("step", 121, step_121))
    step_122 = order.quantity_at(122) * catalog.price_at(122)
    total = total + step_122
    report.append(("step", 122, step_122))
    step_123 = order.quantity_at(123) * catalog.price_at(123)
    total = total + step_123
    report.append(("step", 123, step_123))
    step_124 = order.quantity_at(124) * catalog.price_at(124)
    total = total + step_124
    report.append(("step", 124, step_124))
    step_125 = order.quantity_at(125) * catalog.price_at(125)
    total = total + step_125
    report.append(("step", 125, step_125))
    step_126 = order.quantity_at(126) * catalog.price_at(126)
    total = total + step_126
    report.append(("step", 126, step_126))
    step_127 = order.quantity_at(127) * catalog.price_at(127)
    total = total + step_127
    report.append(("step", 127, step_127))
    step_128 = order.quantity_at(128) * catalog.price_at(128)
    total = total + step_128
    report.append(("step", 128, step_128))
    step_129 = order.quantity_at(129) * catalog.price_at(129)
    total = total + step_129
    report.append(("step", 129, step_129))
    step_130 = order.quantity_at(130) * catalog.price_at(130)
    total = total + step_130
    report.append(("step", 130, step_130))
    step_131 = order.quantity_at(131) * catalog.price_at(131)
    total = total + step_131
    report.append(("step", 131, step_131))
    step_132 = order.quantity_at(132) * catalog.price_at(132)
    total = total + step_132
    report.append(("step", 132, step_132))
    step_133 = order.quantity_at(133) * catalog.price_at(133)
    total = total + step_133
    report.append(("step", 133, step_133))
    step_134 = order.quantity_at(134) * catalog.price_at(134)
    total = total + step_134
    report.append(("step", 134, step_134))
    step_135 = order.quantity_at(135) * catalog.price_at(135)
    total = total + step_135
    report.append(("step", 135, step_135))
    step_136 = order.quantity_at(136) * catalog.price_at(136)
    total = total + step_136
    report.append(("step", 136, step_136))
    step_137 = order.quantity_at(137) * catalog.price_at(137)
    total = total + step_137
    report.append(("step", 137, step_137))
    step_138 = order.quantity_at(138) * catalog.price_at(138)
    total = total + step_138
    report.append(("step", 138, step_138))
    step_139 = order.quantity_at(139) * catalog.price_at(139)
    total = total + step_139
    report.append(("step", 139, step_139))
    return total, report
