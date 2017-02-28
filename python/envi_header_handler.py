import os
author = 'Steve Kochaver'

class ENVI_Header:

    def __init__(self, hdr_path):

        self.hdr_dict, self._key_order, self._nested_keys = self._get_hdr_dict(hdr_path)
        self.hdr_dict = self._mod_nested_vals(self.hdr_dict, self._nested_keys)

    def get_keys(self):
        return self._key_order

    def get_value(self, value_key):
        return self.hdr_dict[value_key]

    def change_value(self, value_key, new_value):
        self.hdr_dict[value_key] = new_value
        return

    def get_rotation(self):
        map_info = self.get_value('map info')
        for info in map_info:
            if 'rotation' in info:
                return float(info.split('=')[-1].strip())
        return 0.0

    def write_header(self, target_directory, target_file_name):
        '''
        Write a new header at target path using the ENVI_Header object's current header dictionary variable.
        Attempts to write out in a format functionally identical, but visually cleaner.
        :param target_directory: Location for the output .hdr file
        :param target_file_name: File name of the new .hdr file
        :return:
        '''

        with open(os.path.join(target_directory, target_file_name), 'w+') as new_hdr:

            new_hdr.write('ENVI \n\n')  # Write the first line as convention dictates.

            for key in self._key_order:  # Loop through all keys in the object's dictionary attribute

                new_hdr.write(str(key))
                new_hdr.write(' = ')  # Turn the key, value pair into an inline equality.

                # Logical block to correctly format nested values in the way ENVI headers like it.
                if key in self._nested_keys:

                    new_hdr.write('{')  # Start the curly bracket nesting designation

                    try:  # Eventually switch to a more robust system. This just tries to avoid non-listed nested values
                        new_hdr.write(', '.join(self.hdr_dict[key]))

                    except:
                        new_hdr.write(self.hdr_dict[key])

                    new_hdr.write('}')  # Close the curly brackets on the same line

                else:
                    new_hdr.write(self.hdr_dict[key])

                new_hdr.write('\n'*2)  # Functional lines separated with two newline characters for readability.

    def _get_hdr_dict(self, hdr_path):
        """
        Reads an ENVI header file and turns the properties into a python dictionary for ease of reading and changing values.
        :param hdr_path: Path to the header file of interest.
        :return: Returns a python dictonary object of ENVI header properties and a list of keys in the order they were read.
        """

        # Create empty objects for appending as we iterate through the file.
        hdr_dict = {}
        _key_order = []
        _nested_keys = []

        # Open the file and create lines iterable.
        header_file = open(hdr_path, 'r')
        lines = header_file.readlines()

        # Create empty variable to change as we encounter new key values
        current_key = ''
        nested = False

        for line in lines:

            if nested:
                hdr_dict[current_key] += line.strip()
                if "}" in line:
                        nested = False

            else:
                if '=' in line:  # Check for equalities. That's where properties are defined.
                    key, value = line.split('=', 1)  # Split line with equality; use first value as key.

                    current_key = key.strip()
                    hdr_dict[current_key] = value.strip()
                    _key_order.append(current_key)

                    if "{" in value:
                        nested = True
                        _nested_keys.append(current_key)
                    if "}" in line:
                        nested = False

                    pass

                elif line == 'ENVI\n':  # This is usually the first line. It can be skipped.
                    pass

                else:  # Pass over any unforseen issues.
                    pass

        header_file.close()

        return hdr_dict, _key_order, _nested_keys

    def _mod_nested_vals(self, hdr_dict, _nested_keyes, delim=','):
        '''
        Break a nested header dictionary value into a list of constituent values. Useful for further parsing.
        :param hdr_dict: Class variable header dictionary
        :param _nested_keyes: Class variable
        :param delim:  Delimeter type that denotes breaks in the nested values. Defaults to commas (semicolon cases confirmed for seemingly non-functional values [i.e. description strings])
        :return:
        '''
        for key in _nested_keyes:
            raw_val = hdr_dict[key]

            try:  # This may need a "delimiter not recognized" warning
                raw_list = raw_val.replace('{', '').replace('}', '').split(',')
                clean_list = []
                for val in raw_list:
                    clean_list.append(val.replace('\n', '').replace('\t', '').strip())
                    hdr_dict[key] = clean_list

            except:
                pass  # Probably not safe

        return hdr_dict