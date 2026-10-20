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
