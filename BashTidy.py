import sublime
import sublime_plugin
import re


class BashtidyCommand(sublime_plugin.TextCommand):

    def beautify_string(self, data):
        tab = 0
        case_stack = []
        in_here_doc = False
        defer_ext_quote = False
        in_ext_quote = False
        ext_quote_string = ''
        here_string = ''
        output = []
        line = 1
        for record in re.split('\n', data):
            record = record.rstrip()
            stripped_record = record.strip()

            # collapse multiple quotes between ' ... '
            test_record = re.sub(r'\'.*?\'', '', stripped_record)
            # collapse multiple quotes between " ... "
            test_record = re.sub(r'".*?"', '', test_record)
            # collapse multiple quotes between ` ... `
            test_record = re.sub(r'`.*?`', '', test_record)
            # collapse multiple quotes between \` ... ' (weird case)
            test_record = re.sub(r'\\`.*?\'', '', test_record)
            # strip out any escaped single characters
            test_record = re.sub(r'\\.', '', test_record)
            # remove '#' comments
            test_record = re.sub(r'(\A|\s)(#.*)', '', test_record, 1)
            if(not in_here_doc):
                if(re.search('<<-?', test_record)):
                    here_string = re.sub(
                        '.*<<-?\s*[\'|"]?([_|\w]+)[\'|"]?.*', '\\1',
                        stripped_record, 1)
                    in_here_doc = (len(here_string) > 0)
            if(in_here_doc):  # pass on with no changes
                output.append(record)
                # now test for here-doc termination string
                if(re.search(here_string, test_record)
                   and not re.search('<<', test_record)):
                    in_here_doc = False
            else:  # not in here doc
                if(in_ext_quote):
                    if(re.search(ext_quote_string, test_record)):
                        # provide line after quotes
                        test_record = re.sub(
                            '.*%s(.*)' % ext_quote_string, '\\1', test_record, 1)
                        in_ext_quote = False
                else:  # not in ext quote
                    if(re.search(r'(\A|\s)(\'|")', test_record)):
                        # apply only after this line has been processed
                        defer_ext_quote = True
                        ext_quote_string = re.sub(
                            '.*([\'"]).*', '\\1', test_record, 1)
                        # provide line before quote
                        test_record = re.sub(
                            '(.*)%s.*' % ext_quote_string, '\\1', test_record, 1)
                if(in_ext_quote):
                    # pass on unchanged
                    output.append(record)
                else:  # not in ext quote
                    inc = len(
                        re.findall('(\s|\A|;)(case|then|do)(;|\Z|\s)',
                                   test_record))
                    inc += len(re.findall('(\{|\(|\[)', test_record))
                    outc = len(
                        re.findall(
                            '(\s|\A|;)(esac|fi|done|elif)(;|\)|\||\Z|\s)',
                            test_record))
                    outc += len(re.findall('(\}|\)|\])', test_record))
                    if(re.search(r'\besac\b', test_record)):
                        if(len(case_stack) == 0):
                            self.view.set_status(
                                'bashtidy',  '"esac" before "case" in ' + line + 'line')
                        else:
                            outc += case_stack.pop()
                    # sepcial handling for bad syntax within case ... esac
                    if(len(case_stack) > 0):
                        if(re.search('\A[^(]*\)', test_record)):
                            # avoid overcount
                            outc -= 2
                            case_stack[-1] += 1
                        if(re.search(';;', test_record)):
                            outc += 1
                            case_stack[-1] -= 1
                    # an ad-hoc solution for the "else" keyword
                    else_case = (0, -1)[
                        re.search('^(else|elif)', test_record) != None]
                    net = inc - outc
                    tab += min(net, 0)
                    extab = tab + else_case
                    extab = max(0, extab)
                    output.append(
                        (self.tab_str * self.tab_size * extab) + stripped_record)
                    tab += max(net, 0)
                if(defer_ext_quote):
                    in_ext_quote = True
                    defer_ext_quote = False
                if(re.search(r'\bcase\b', test_record)):
                    case_stack.append(0)
            line += 1
        error = (tab != 0)
        if(error):
            self.view.set_status(
                'bashtidy', 'indent/outdent mismatch: ' + tab)
        return '\n'.join(output)

    def run(self, edit):
        self.tab_str = ' '
        self.tab_size = 4

        if self.view.sel()[0].empty():
            xmlRegion = sublime.Region(0, self.view.size())
        else:
            xmlRegion = self.view.sel()[0]

        result = self.beautify_string(
            self.view.substr(xmlRegion))

        self.view.replace(
            edit, xmlRegion, result.replace("\r", ""))
