#!/usr/bin/env python3
"""The book roster, shared by the builder and the invariant gate.

It lives in its own module so the gate can check the SPECIFIED page range of
each book (via idx_range) instead of the range that happened to render — a
duplicated copy would drift the moment a volume is re-sliced."""

BOOKS = [
    dict(id="samagam-purvardh",  title_gu="સમાગમ (પૂર્વાર્ધ)",  title_en="Samagam — Purvardh",  language="gu"),
    dict(id="samagam-uttarardh", title_gu="સમાગમ (ઉત્તરાર્ધ)", title_en="Samagam — Uttarardh", language="gu"),
    dict(id="kirtan-gujarati",   title_gu="શ્રી અધ્યારુજીનાં કીર્તન", title_en="Shree Padmanabhji Adhyaruji na Kirtan", language="gu",
         idx_range=(1, 38)),
    dict(id="jivandas-sakhi",    title_gu="વૈષ્ણવ જીવણદાસજીકી સાખી", title_en="Vaishnav Jivandasji ki Sakhi", language="gu",
         src="kirtan-gujarati", idx_range=(39, 64)),
    dict(id="kirtan-english",    title_gu="અધ્યારુજીનાં કીર્તન (અંગ્રેજી)", title_en="Adhyaruji na Kirtan — English transliteration", language="translit"),
    dict(id="sant-darshan",      title_gu="સંત દર્શન",           title_en="Sant Darshan",        language="gu"),
]
