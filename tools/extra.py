# Characters the page's two texts need that the fonts don't have yet, put together
# here from parts the fonts already draw. Each one leaves this file when a round of
# the fonts draws it.
# 蘭亭集序 (the forms the 神龍本 writes): 脩禊事也, 暎帶左右, 俛仰之間.
C['禊'] = lr(L['礻'], C['契'])
C['暎'] = lr(L['日'], C['英'])
C['俛'] = lr(L['亻'], C['免'])
# 前赤壁賦: 寄蜉蝣於天地.
C['蜉'] = box((K['虫'], (0, 100, 440, 900)), (K['孚'], (380, 0, 1000, 1000)))
C['蝣'] = box((K['虫'], (0, 100, 440, 900)), (K['斿'], (380, 0, 1000, 1000)))
