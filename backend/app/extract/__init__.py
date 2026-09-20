from . import chiba_city, kanagawa, kitakyushu, kyoto, okinawa

PARSERS = {
    "神奈川県": kanagawa.parse,
    "千葉市": chiba_city.parse,
    "北九州市": kitakyushu.parse,
    "京都府": kyoto.parse,
    "沖縄県": okinawa.parse,
}
