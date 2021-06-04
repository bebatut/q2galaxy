# ----------------------------------------------------------------------------
# Copyright (c) 2018-2021, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import re
import lxml.etree as xml
import collections
from datetime import datetime

import qiime2
import qiime2.sdk as sdk

import q2galaxy


class OrderedTool(collections.OrderedDict):
    order = ["description", "macros", "edam_topics", "edam_operations",
             "parallelism", "requirements", "code", "stdio", "version_command",
             "command", "environment_variables", "configfiles", "inputs",
             "request_param_translation", "outputs", "tests", "help",
             "citations"]
    order_attr = ['name', 'argument', 'type', 'format', 'min', 'truevalue',
                  'max', 'falsevalue', 'value', 'checked', 'optional', 'label',
                  'help']
    order_attr_set = set(order_attr)

    def __init__(self, items):
        order_items = []
        remaining_items = []
        for item in items:
            if item[0] in self.order_attr_set:
                order_items.append(item)
            else:
                remaining_items.append(item)

        order_items.sort(key=lambda x: self.order_attr.index(x[0]))
        remaining_items.sort(key=lambda x: x[0])

        super().__init__([*order_items, *remaining_items])

    @classmethod
    def sorted(cls, e):
        new = cls._sorted_attrs(e)
        new[:] = sorted(new, key=lambda x: cls.order.index(x.tag))
        return new

    @classmethod
    def _sorted_attrs(cls, e):
        new = xml.Element(e.tag, cls(e.attrib.items()))
        new.text = e.text
        for child in e:
            new.append(cls._sorted_attrs(child))
        return new


def XMLNode(name_, _text=None, **attrs):
    e = xml.Element(name_, attrs)
    if _text is not None:
        e.text = _text
    return e


def write_tool(tool, filepath):
    tool = OrderedTool.sorted(tool)
    tool.set('profile', '20.09')
    tool.set('license', 'BSD-3-Clause')
    tool.addprevious(xml.Comment(COPYRIGHT))
    tool.addprevious(xml.Comment(
        "\nThis tool was automatically generated by:\n"
        f"    q2galaxy (version: {q2galaxy.__version__})\n"
        "for:\n"
        f"    qiime2 (version: {qiime2.__version__})\n"))

    tool = xml.ElementTree(tool)
    xml.indent(tool, ' ' * 4)
    xmlbytes = xml.tostring(tool, pretty_print=True, encoding='utf-8',
                            xml_declaration=True)
    with open(filepath, 'wb') as fh:
        fh.write(xmlbytes)


def get_mystery_stew():
    from q2_mystery_stew.plugin_setup import create_plugin

    pm = sdk.PluginManager(add_plugins=False)

    test_plugin = create_plugin(
        ints=True,
        strings=True,
        bools=True,
        floats=True,
        artifacts=True,
        primitive_unions=True,
        metadata=True,
        collections=True)

    pm.add_plugin(test_plugin)
    return pm.get_plugin(id='mystery_stew')


# see: https://github.com/galaxyproject/galaxy/blob
#      /2f3096790d4a77ba75b651f4abc43c740687c1e1/lib/galaxy/util
#      /__init__.py#L527-L539
# AKA: galaxy.util:mapped_chars
_escaped = [
    # only `[]` is likely to come up, but better safe than sorry
    ('[', '__ob__'),
    (']', '__cb__'),
    ('>', '__gt__'),
    ('<', '__lt__'),
    ('\'', '__sq__'),
    ('"', '__dq__'),
    ('{', '__oc__'),
    ('}', '__cc__'),
    ('@', '__at__'),
    ('\n', '__cn__'),
    ('\r', '__cr__'),
    ('\t', '__tc__'),
    ('#', '__pd__'),
    # adding this one so that <test/> won't see multiple values
    (',', '__comma__')
]
_mapped = [
    # Custom:
    (None, '__q2galaxy__::literal::None'),
    (True, '__q2galaxy__::literal::True'),
    (False, '__q2galaxy__::literal::False')
]


def galaxy_esc(s):
    if type(s) is str:
        for char, esc in _escaped:
            s = s.replace(char, esc)
        return s
    else:
        for val, esc in _mapped:
            if s is val:
                return esc
    raise NotImplementedError


def galaxy_unesc(s):
    for val, esc in _mapped:
        if esc == s:
            return val

    for char, esc in _escaped:
        s = s.replace(esc, char)
    return s


def galaxy_ui_var(*, value=None, tag=None, name=None):
    if value is not None:
        return f'__q2galaxy__::control::{value}'

    elements = ['', 'q2galaxy', 'GUI']
    if tag is not None:
        elements.append(tag)
    if name is not None:
        elements.append(name)

    elements.append('')
    return '__'.join(elements)


def pretty_fmt_name(format_obj):
    # from SO: https://stackoverflow.com/a/9283563/579416
    spaced = re.sub(
        r"""
        (            # start the group
            # alternative 1
        (?<=[a-z])  # current position is preceded by a lower char
                    # (positive lookbehind: does not consume any char)
        [A-Z]       # an upper char
                    #
        |   # or
            # alternative 2
        (?<!\A)     # current position is not at the beginning of the str
                    # (negative lookbehind: does not consume any char)
        [A-Z]       # an upper char
        (?=[a-z])   # matches if next char is a lower char
                    # lookahead assertion: does not consume any char
        )           # end the group
        """, r' \1', format_obj.__name__, flags=re.VERBOSE)

    final = []
    for token in spaced.split(' '):
        if token == 'Fmt':
            token = 'Format'
        elif token == 'Dir':
            token = 'Directory'

        final.append(token)

    return ' '.join(final)


def rst_header(header, level):
    fill = ['=', '-', '*', '^'][level-1]
    return '\n'.join(['', header, fill * len(header), ''])


COPYRIGHT = f"""
Copyright (c) {datetime.now().year}, QIIME 2 development team.

Distributed under the terms of the Modified BSD License. (SPDX: BSD-3-Clause)
"""
