"""Idiomas que sabe cubrir Fontificar: qué caracteres agrega y cómo renombra la familia."""
from typing import NamedTuple


class Idioma(NamedTuple):
    caracteres: str
    sufijo: str  # se agrega al nombre de la familia
    sufijo_ps: str  # el nombre PostScript solo admite ASCII
    muestra: str


IDIOMAS = {
    "es": Idioma("áéíóúüñÁÉÍÓÚÜÑ¡¿´¨", "Español", "Espanol",
                 "Canción, pingüino, ¿Qué tal? ¡Hola!"),
    "latin1": Idioma(
        "ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÑÒÓÔÕÖØÙÚÛÜÝßàáâãäåæçèéêëìíîïñòóôõöøùúûüýÿŒœŸ¡¿´¨¸",
        "Latino", "Latino",
        "Façade, crème brûlée, Ångström, smørrebrød, cœur, naïveté, Straße, ¿Qué tal?"),
    # `·` va antes que Ŀ ŀ: se arman con ese glifo ya agregado.
    "latinext": Idioma(
        "ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÑÒÓÔÕÖØÙÚÛÜÝßàáâãäåæçèéêëìíîïñòóôõöøùúûüýÿŒœŸ¡¿·"
        "ĀāĂăĄąĆćĈĉĊċČčĎďĐđĒēĔĕĖėĘęĚěĜĝĞğĠġĢģĤĥĦħĨĩĪīĬĭĮįİıĲĳĴĵĶķĸĹĺĻļĽľĿŀŁł"
        "ŃńŅņŇňŌōŎŏŐőŔŕŖŗŘřŚśŜŝŞşŠšŢţŤťŦŧŨũŪūŬŭŮůŰűŲųŴŵŶŷŹźŻżŽžẞ´¨¸¯˘˙˝ˇ˛",
        "Latino Extendido", "LatinoExtendido",
        "Łódź, wąż, žluťoučký kůň, İzmir, ağaç, Đakovo, Ħamrun, Őrség, Straße, ¿Qué tal?"),
}
# El más completo: `latinext` más las letras y los símbolos que faltan de Latin-1 y
# Windows-1252. ’ va antes que las demás comillas y ‹ › antes que « ».
# Las rayas van por su codepoint (U+2013, U+2014), no como caracter.
IDIOMAS["fontificata"] = Idioma(
    IDIOMAS["latinext"].caracteres + "ÐðÞþŊŋ’‘‚”“„\u2013\u2014…•‹›«»ªº¹²³¼½¾€£¢¥©®°±×÷¬¦§¶¤µ",
    "Fontificata", "Fontificata",
    "«¿Qué tal?», dijo ‘Þór’ en Łódź: 3½ kg a 25 °C, ±5 € × 2 = 10 £, ª º ¹ ² ³ § ¶ © ®…")
