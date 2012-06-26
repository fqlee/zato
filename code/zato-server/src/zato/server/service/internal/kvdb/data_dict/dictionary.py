# -*- coding: utf-8 -*-

"""
Copyright (C) 2012 Dariusz Suchojad <dsuch at gefira.pl>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

# stdlib
import re

# Zato
from zato.common import KVDB, ZatoException
from zato.server.service.internal import AdminService

class _DictionaryService(AdminService):
    def _get_dict_items(self):
        for id, item in self.server.kvdb.conn.hgetall(KVDB.DICTIONARY_ITEM).items():
            system, key, value = item.split(KVDB.SEPARATOR)
            yield {'id':id, 'system':system, 'key':key, 'value':value}

class GetList(_DictionaryService):
    """ Returns a list of dictionary items.
    """
    class SimpleIO:
        output_required = ('id', 'system', 'key', 'value')
        
    def get_data(self):
        return self._get_dict_items()

    def handle(self):
        self.response.payload[:] = self.get_data()

class _CreateEdit(_DictionaryService):
    NAME_PATTERN = '\w+'
    NAME_RE = re.compile(NAME_PATTERN)
    
    class SimpleIO:
        input_required = ('system', 'key', 'value')
        input_optional = ('id',)
        output_optional = ('id',)
        
    def _validate_entry(self, validate_item, id=None):
        for elem in('system', 'key'):
            name = self.request.input[elem]
            match = self.NAME_RE.match(name)
            if match and match.group() == name:
                continue
            else:
                msg = "System and key may contain only letters, digits and an underscore, failed to validate [{}] against the regular expression {}".format(name, self.NAME_PATTERN)
                raise ZatoException(self.cid, msg)
        
        for item in self._get_dict_items():
            joined = KVDB.SEPARATOR.join((item['system'], item['key'], item['value']))
            if validate_item == joined and id != item['id']:
                msg = 'The triple of system:[{}], key:[{}], value:[{}] already exists'.format(item['system'], item['key'], item['value'])
                raise ZatoException(self.cid, msg)

        return True
    
    def _get_item_name(self):
        return KVDB.SEPARATOR.join((self.request.input.system, self.request.input.key, self.request.input.value))
    
    def handle(self):
        item = self._get_item_name()
        
        if self.request.input.get('id'):
            id = self.request.input.id
        else:
            ids = self.server.kvdb.conn.hkeys(KVDB.DICTIONARY_ITEM)
            id = (max(int(elem) for elem in ids) + 1) if ids else 1
            
        id = str(id)
            
        if self._validate_entry(item, id):
            self.server.kvdb.conn.hset(KVDB.DICTIONARY_ITEM, id, item)
            
        self.response.payload.id = id

class Create(_CreateEdit):
    """ Creates a new dictionary entry.
    """
    # Does nothing more than the superclass already does
    
class Edit(_CreateEdit):
    """ Creates a new dictionary entry.
    """
    # Does nothing more than the superclass already does

class Delete(AdminService):
    """ Deletes a dictionary entry by its ID.
    """
    class SimpleIO:
        input_required = ('id',)
        output_required = ('id',)
        
    def handle(self):
        self.server.kvdb.conn.hdel(KVDB.DICTIONARY_ITEM, self.request.input.id)
        self.response.payload.id = self.request.input.id