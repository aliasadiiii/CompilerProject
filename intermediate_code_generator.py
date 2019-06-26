class SemanticException(Exception):
    def __init__(self, message):
        self.message = message
        super(SemanticException, self).__init__()


class IntermediateCodeGenerator(object):
    def __init__(self):
        self.is_ok = True
        self.scope = 0

        self.symbol_table = {('output', 0): ('func', 1, 200, 'void', 1)}
        self.semantic_stack = []

        self.program_block = [(), ('ASSIGN', '#0', 202, None),
                              ('PRINT', 200, None, None),
                              ('JP', '@201', None, None)]
        self.data_ptr = 203
        self.temporary_ptr = 500

    def get_temp(self):
        ptr = self.temporary_ptr
        self.temporary_ptr += 1
        return ptr

    def get_scope(self, name):
        late_scope = -1
        for key, sc in self.symbol_table.keys():
            if key == name:
                late_scope = max(late_scope, sc)
        return late_scope

    def run_routine(self, method):
        if not self.is_ok:
            return

        if method == 'int-dec':
            name = self.semantic_stack.pop()
            kind = self.semantic_stack.pop()
            if kind == 'void':
                raise SemanticException("Illegal type of void.")
            self.symbol_table[(name, self.scope)] = (kind, self.data_ptr)
            self.data_ptr += 1

        if method == 'arr-dec':
            cnt = int(self.semantic_stack.pop()[1:])
            name = self.semantic_stack.pop()
            kind = self.semantic_stack.pop()
            if kind == 'void':
                raise SemanticException("Illegal type of void.")
            self.symbol_table[(name, self.scope)] = ('arr', self.data_ptr)
            self.data_ptr += cnt

        if method == 'start-func-dec':
            name = self.semantic_stack.pop()
            kind = self.semantic_stack.pop()
            self.scope += 1
            self.semantic_stack.append(len(self.program_block))
            self.semantic_stack.append(kind)
            self.semantic_stack.append(name)
            self.program_block.append(())
            self.semantic_stack.append(0)

        if method == 'func-int-dec':
            name = self.semantic_stack.pop()
            kind = self.semantic_stack.pop()
            self.semantic_stack[-1] += 1
            if kind == 'void':
                raise SemanticException("Illegal type of void.")
            self.symbol_table[(name, self.scope)] = ('int', self.data_ptr)
            self.data_ptr += 1

        if method == 'func-arr-dec':
            name = self.semantic_stack.pop()
            kind = self.semantic_stack.pop()
            self.semantic_stack[-1] += 1
            if kind == 'void':
                raise SemanticException("Illegal type of void.")
            self.symbol_table[(name, self.scope)] = ('arr', self.data_ptr)
            self.data_ptr += 1

        if method == 'end-func-dec':
            cnt = self.semantic_stack.pop()
            if cnt == 'void':
                self.semantic_stack.pop()
                cnt = 0
            name = self.semantic_stack.pop()
            kind = self.semantic_stack.pop()

            self.scope -= 1
            self.symbol_table[(name, self.scope)] = \
                ('func', len(self.program_block),
                 self.data_ptr - cnt, kind, cnt)

            self.semantic_stack.append('func')
            self.semantic_stack.append(self.data_ptr)
            self.program_block.append(('ASSIGN', '#0', self.data_ptr + 1, None))
            self.data_ptr += 2

        if method == 'start-scope':
            self.scope += 1

        if method == 'end-scope':
            self.symbol_table = {(key, sc): self.symbol_table[(key, sc)]
                                 for key, sc in self.symbol_table.keys()
                                 if sc < self.scope}
            self.scope -= 1

        if method == 'get-arr':
            idx = self.semantic_stack.pop()
            name = self.semantic_stack.pop()
            if name not in [key for key, sc in self.symbol_table.keys()]:
                raise SemanticException("'%s' is not defined." % name)
            if self.symbol_table[(name, self.get_scope(name))][0] != 'arr':
                raise SemanticException("Type mismatch in operands.")
            ptr = self.get_temp()
            self.program_block.append(('ADD', idx, '#%s' % self.symbol_table[(name, self.get_scope(name))][1], ptr))
            self.semantic_stack.append('@%s' % ptr)

        if method == 'get-int':
            name = self.semantic_stack.pop()
            if name not in [key for key, sc in self.symbol_table.keys()]:
                raise SemanticException("'%s' is not defined." % name)
            if self.symbol_table[(name, self.get_scope(name))][0] not in ['int', 'arr']:
                raise SemanticException("Type mismatch in operands.")
            self.semantic_stack.append(self.symbol_table[(name, self.get_scope(name))][1])

        if method == 'assign':
            source = self.semantic_stack.pop()
            dest = self.semantic_stack.pop()
            self.program_block.append(('ASSIGN', source, dest, None))
            self.semantic_stack.append(dest)

        if method == 'negate':
            source = self.semantic_stack.pop()
            ptr = self.get_temp()
            self.program_block.append(('SUB', '#0', source, ptr))
            self.semantic_stack.append(ptr)

        if method == 'multiply':
            op1 = self.semantic_stack.pop()
            op2 = self.semantic_stack.pop()
            ptr = self.get_temp()
            self.program_block.append(('MULT', op1, op2, ptr))
            self.semantic_stack.append(ptr)

        if method == 'sub-char':
            self.semantic_stack.append('-')

        if method == 'check-negate':
            if len(self.semantic_stack) > 1 and self.semantic_stack[-2] == '-':
                op1 = self.semantic_stack.pop()
                self.semantic_stack.pop()
                ptr = self.get_temp()
                self.program_block.append(('SUB', '#0', op1, ptr))
                self.semantic_stack.append(ptr)

        if method == 'addop':
            op1 = self.semantic_stack.pop()
            op2 = self.semantic_stack.pop()
            ptr = self.get_temp()

            self.program_block.append(('ADD', op2, op1, ptr))
            self.semantic_stack.append(ptr)

        if method == 'start-call':
            name = self.semantic_stack.pop()
            if name not in [key for key, sc in self.symbol_table.keys()]:
                raise SemanticException("'%s' is not defined." % name)
            self.semantic_stack.append(name)
            self.semantic_stack.append(self.symbol_table[(name, self.get_scope(name))][2])
            self.semantic_stack.append(self.symbol_table[(name, self.get_scope(name))][4])

        if method == 'add-call-arg':
            exp = self.semantic_stack.pop()
            cnt = self.semantic_stack.pop()
            if cnt == 0:
                self.semantic_stack.pop()
                name = self.semantic_stack.pop()
                raise SemanticException("Mismatch in numbers of arguments of '%s'." % name)

            idx = self.semantic_stack.pop()
            self.program_block.append(('ASSIGN', exp, idx, None))
            self.semantic_stack.append(idx + 1)
            self.semantic_stack.append(cnt - 1)

        if method == 'end-call':
            cnt = self.semantic_stack.pop()
            idx = self.semantic_stack.pop()
            name = self.semantic_stack.pop()
            if cnt:
                raise SemanticException("Mismatch in numbers of arguments of '%s'." % name)

            ptr = self.get_temp()
            self.program_block.append(('ASSIGN', "#%d" % (len(self.program_block) + 2), idx, None))
            self.program_block.append(('JP', self.symbol_table[(name, self.get_scope(name))][1], None, None))
            self.program_block.append(('ASSIGN', idx + 1, ptr, None))
            self.semantic_stack.append(ptr)

        if method == 'pop':
            self.semantic_stack.pop()

        if method == 'return-value':
            exp = self.semantic_stack.pop()
            idx = -1
            for i in range(len(self.semantic_stack)-1, -1, -1):
                if self.semantic_stack[i] == 'func':
                    idx = self.semantic_stack[i+1]
            self.program_block.append(('ASSIGN', exp, idx + 1, None))

        if method == 'return-call':
            idx = -1
            for i in range(len(self.semantic_stack)-1, -1, -1):
                if self.semantic_stack[i] == 'func':
                    idx = self.semantic_stack[i+1]
            self.program_block.append(('JP', '@%s' % idx, None, None))

        if method == 'end-func':
            idx = self.semantic_stack.pop()
            if 'main' not in [key for key, sc in self.symbol_table.keys()]:
                self.program_block.append(('JP', '@%s' % idx, None, None))

            self.semantic_stack.pop()
            idx = self.semantic_stack.pop()
            self.program_block[idx] = ('JP', len(self.program_block), None, None)

        if method == 'end-program':
            if 'main' not in [key for key, sc in self.symbol_table.keys()]:
                raise SemanticException('main function not found!')

            self.program_block[0] = ('JP', self.symbol_table[('main', self.get_scope('main'))][1], None, None)

        if method == 'save':
            self.semantic_stack.append(len(self.program_block))
            self.program_block.append(())

        if method == 'lt-char':
            self.semantic_stack.append('<')

        if method == 'eq-char':
            self.semantic_stack.append('==')

        if method == 'relop':
            op2 = self.semantic_stack.pop()
            operation = 'LT' if self.semantic_stack.pop() == '<' else 'EQ'
            op1 = self.semantic_stack.pop()

            ptr = self.get_temp()
            self.program_block.append((operation, op1, op2, ptr))
            self.semantic_stack.append(ptr)

        if method == 'if-jump':
            idx = self.semantic_stack.pop()
            exp = self.semantic_stack.pop()

            self.program_block[idx] = ('JPF', exp, len(self.program_block) + 1, None)
            self.semantic_stack.append(len(self.program_block))
            self.program_block.append(())

        if method == 'else-jump':
            idx = self.semantic_stack.pop()
            self.program_block[idx] = ('JP', len(self.program_block), None, None)

        if method == 'label':
            self.program_block.append(('JP', len(self.program_block) + 2, None, None))
            self.program_block.append(())
            self.semantic_stack.append(len(self.program_block))

        if method == 'while-save':
            self.semantic_stack.append('while')
            self.semantic_stack.append(len(self.program_block))
            self.program_block.append(())

        if method == 'while':
            idx = self.semantic_stack.pop()
            self.semantic_stack.pop()
            exp = self.semantic_stack.pop()
            label = self.semantic_stack.pop()

            self.program_block[idx] = ('JPF', exp, len(self.program_block) + 1, None)
            self.program_block.append(('JP', label, None, None))
            self.program_block[label-1] = ('JP', len(self.program_block), None, None)

        if method == 'continue':
            if 'while' not in self.semantic_stack:
                raise SemanticException("No 'while' found for 'continue'.")

            idx = len(self.semantic_stack) - self.semantic_stack[::-1].index('while') - 3
            self.program_block.append(('JP', self.semantic_stack[idx], None, None))

        if method == 'start-switch':
            self.semantic_stack.append('switch')

        if method == 'switch-save':
            num = self.semantic_stack.pop()
            self.semantic_stack.pop()  # switch
            exp = self.semantic_stack.pop()
            ptr = self.get_temp()
            self.program_block.append(('EQ', exp, num, ptr))

            self.semantic_stack.append(exp)
            self.semantic_stack.append('switch')
            self.semantic_stack.append(ptr)
            self.semantic_stack.append(len(self.program_block))
            self.program_block.append(())

        if method == 'case':
            idx = self.semantic_stack.pop()
            ptr = self.semantic_stack.pop()

            self.program_block[idx] = ('JPF', ptr, len(self.program_block) + 1, None)
            self.program_block.append(('JP', len(self.program_block) + 3, None, None))

        if method == 'add2':
            self.program_block.append(('JP', len(self.program_block) + 1, None, None))
            self.program_block.append(('JP', len(self.program_block) + 1, None, None))

        if method == 'switch':
            self.semantic_stack.pop()  # switch
            self.semantic_stack.pop()  # exp
            label = self.semantic_stack.pop()

            self.program_block[label-1] = ('JP', len(self.program_block), None, None)

        if method == 'break':
            if 'switch' not in self.semantic_stack and 'while' not in self.semantic_stack:
                raise SemanticException("No 'while' or 'switch' found for 'break'.")

            for i in range(len(self.semantic_stack)-1, -1, -1):
                if self.semantic_stack[i] in ('while', 'switch'):
                    label = self.semantic_stack[i - 2]
                    self.program_block.append(('JP', label-1, None, None))


