import ast
import re

from antlr4 import InputStream, CommonTokenStream

from luaparser.astnodes import *
from luaparser.parser.LuaLexer import LuaLexer
from typing import List, Tuple, Literal
from antlr4.Token import Token


class SyntaxException(Exception):
    def __init__(self, user_msg, token=None):
        if token:
            message = (
                    "(" + str(token.line) + "," + str(token.start) + "): Error: " + user_msg
            )
        else:
            message = "Error: " + user_msg
        super().__init__(message)


class Expr(Enum):
    OR = 1
    AND = 2
    REL = 3
    CONCAT = 4
    ADD = 5
    MULT = 6
    BITWISE = 7
    UNARY = 8
    POW = 9
    ATOM = 10


# class Tokens:
#     AND = 1
#     BREAK = 2
#     DO = 3
#     ELSETOK = 4
#     ELSEIF = 5
#     END = 6
#     FALSE = 7
#     FOR = 8
#     FUNCTION = 9
#     GOTO = 10
#     IFTOK = 11
#     IN = 12
#     LOCAL = 13
#     NIL = 14
#     NOT = 15
#     OR = 16
#     REPEAT = 17
#     RETURN = 18
#     THEN = 19
#     TRUE = 20
#     UNTIL = 21
#     WHILE = 22
#     ADD = 23
#     MINUS = 24
#     MULT = 25
#     DIV = 26
#     FLOOR = 27
#     MOD = 28
#     POW = 29
#     LENGTH = 30
#     EQ = 31
#     NEQ = 32
#     LTEQ = 33
#     GTEQ = 34
#     LT = 35
#     GT = 36
#     ASSIGN = 37
#     BITAND = 38
#     BITOR = 39
#     BITNOT = 40
#     BITRSHIFT = 41
#     BITRLEFT = 42
#     OPAR = 43
#     CPAR = 44
#     OBRACE = 45
#     CBRACE = 46
#     OBRACK = 47
#     CBRACK = 48
#     COLCOL = 49
#     COL = 50
#     COMMA = 51
#     VARARGS = 52
#     CONCAT = 53
#     DOT = 54
#     SEMCOL = 55
#     NAME = 56
#     NUMBER = 57
#     STRING = 58
#     COMMENT = 59
#     LINE_COMMENT = 60
#     SPACE = 61
#     NEWLINE = 62
#     SHEBANG = 63
#     LongBracket = 64


LITERAL_NAMES = [
    "<INVALID>",
    "'and'",
    "'break'",
    "'do'",
    "'else'",
    "'elseif'",
    "'end'",
    "'false'",
    "'for'",
    "'function'",
    "'goto'",
    "'if'",
    "'in'",
    "'local'",
    "'nil'",
    "'not'",
    "'or'",
    "'repeat'",
    "'return'",
    "'then'",
    "'true'",
    "'until'",
    "'while'",
    "'+'",
    "'-'",
    "'*'",
    "'/'",
    "'//'",
    "'%'",
    "'^'",
    "'#'",
    "'=='",
    "'~='",
    "'<='",
    "'>='",
    "'<'",
    "'>'",
    "'='",
    "'&'",
    "'|'",
    "'~'",
    "'>>'",
    "'<<'",
    "'('",
    "')'",
    "'{'",
    "'}'",
    "'['",
    "']'",
    "'::'",
    "':'",
    "','",
    "'...'",
    "'..'",
    "'.'",
    "';'",
    "NAME",
    "NUMBER",
    "STRING",
    "COMMENT",
    "LINE_COMMENT",
    "SPACE",
    "NEWLINE",
    "SHEBANG",
    "LONG_BRACKET",
]


def _listify(obj):
    if not isinstance(obj, list):
        return [obj]
    else:
        return obj


class Builder:
    CLOSING_TOKEN = [LuaLexer.END, LuaLexer.CBRACE, LuaLexer.CPAR]

    HIDDEN_TOKEN = [
        LuaLexer.SHEBANG,
        LuaLexer.LINE_COMMENT,
        LuaLexer.COMMENT,
        LuaLexer.NEWLINE,
        LuaLexer.SPACE,
        -2,
    ]

    REL_OPERATORS = [
        LuaLexer.LT,
        LuaLexer.GT,
        LuaLexer.LTEQ,
        LuaLexer.GTEQ,
        LuaLexer.NEQ,
        LuaLexer.EQ,
    ]

    def __init__(self, source):
        self._stream = CommonTokenStream(LuaLexer(InputStream(source)))
        # contains a list of CommonTokens
        self._line_count: int = 0
        self._right_index: int = 0
        self._last_expr_type: Optional[int] = None

        # following stack are used to backup values
        self._index_stack: List[int] = []
        self._right_index_stack: List[int] = []
        self.text: str = ""  # last token text
        self.type: int = -1  # last token type

        # contains expected token in case of invalid input code
        self._expected = []

        # comments waiting to be inserted into ast nodes
        self._comments_index_stack: List[int] = []
        self.comments: List[Comment] = []
        self._hidden_handled: bool = False
        self._hidden_handled_stack: List[bool] = []

        # special case for stupid PIPE in function call
        self._pipe_in_function_call: bool = False

    @property
    def _LT(self) -> CommonToken:
        """Last token that was consumed in next_i*_* method."""
        return self._stream.LT(-1)

    def process(self) -> Chunk:
        node = self.parse_chunk()

        if not node:
            raise SyntaxException("Expecting a chunk")
        return node

    def save(self):
        # logging.debug('trying ' + inspect.stack()[1][3])
        self._index_stack.append(self._stream.index)
        self._right_index_stack.append(self._right_index)
        self._comments_index_stack.append(len(self.comments))
        self._hidden_handled_stack.append(self._hidden_handled)

    def success(self):
        self._index_stack.pop()
        self._right_index_stack.pop()
        self._comments_index_stack.pop()
        self._hidden_handled_stack.pop()
        return True

    def failure(self):
        self._stream.seek(self._index_stack.pop())
        self._right_index = self._right_index_stack.pop()
        self._hidden_handled = self._hidden_handled_stack.pop()
        n_elem_to_delete = len(self.comments) - self._comments_index_stack.pop()
        if n_elem_to_delete >= 1:
            del self.comments[-n_elem_to_delete:]
        return False

    def failure_save(self):
        self._stream.seek(self._index_stack.pop())
        self._right_index = self._right_index_stack.pop()
        self._hidden_handled = self._hidden_handled_stack.pop()
        n_elem_to_delete = len(self.comments) - self._comments_index_stack.pop()
        if n_elem_to_delete >= 1:
            del self.comments[-n_elem_to_delete:]

        self._index_stack.append(self._stream.index)
        self._right_index_stack.append(self._right_index)
        self._comments_index_stack.append(len(self.comments))
        self._hidden_handled_stack.append(self._hidden_handled)

    def next_is_rc(
            self, type_to_seek: int, hidden_right: bool = True
    ) -> Optional[Token]:
        token = self._stream.LT(1)
        tok_type: int = token.type
        self._right_index = self._stream.index

        if tok_type == type_to_seek:
            self.text = token.text
            self.type = tok_type
            self._stream.consume()
            self._hidden_handled = False
            if hidden_right:
                self.handle_hidden_right()
            return token
        self._expected.append(type_to_seek)
        return None

    def next_is_c(self, type_to_seek: int, hidden_right: bool = True) -> bool:
        token = self._stream.LT(1)
        tok_type: int = token.type
        self._right_index = self._stream.index

        if tok_type == type_to_seek:
            self._stream.consume()
            self._hidden_handled = False
            if hidden_right:
                self.handle_hidden_right()
            return True
        self._expected.append(type_to_seek)
        return False

    def next_is(self, type_to_seek) -> bool:
        if self._stream.LT(1).type == type_to_seek:
            return True
        else:
            self._expected.append(type_to_seek)
            return False

    def prev_is(self, type_to_seek) -> bool:
        return self._stream.LT(-1).type == type_to_seek

    def next_in_rc(self, types: List[int], hidden_right: bool = True) -> bool:
        token = self._stream.LT(1)
        tok_type: int = token.type
        self._right_index = self._stream.index

        if tok_type in types:
            self.type = tok_type
            self._stream.consume()
            self._hidden_handled = False
            if hidden_right:
                self.handle_hidden_right()
            return True
        self._expected.extend(types)
        return False

    def next_in(self, types: List[int]) -> bool:
        if self._stream.LT(1).type in types:
            return True
        else:
            self._expected.extend(types)
            return False

    def handle_hidden_left(self) -> None:
        if self._hidden_handled:
            return
        tokens = self._stream.getHiddenTokensToLeft(self._stream.index)
        if tokens:
            for t in tokens:
                if t.type == LuaLexer.LINE_COMMENT:
                    self.comments.append(
                        Comment(
                            t.text,
                            first_token=t,
                            last_token=t,
                        )
                    )
                elif t.type == LuaLexer.COMMENT:
                    self.comments.append(
                        Comment(
                            t.text,
                            True,
                            first_token=t,
                            last_token=t,
                        )
                    )
                elif t.type == LuaLexer.NEWLINE:
                    # append n time a None value (indicate newline)
                    self.comments += t.text.count("\n") * [None]

        self._hidden_handled = True

    def handle_hidden_right(self) -> None:
        if self._hidden_handled:
            return
        tokens = self._stream.getHiddenTokensToRight(self._right_index)
        if tokens:
            for t in tokens:
                if t.type == LuaLexer.LINE_COMMENT:
                    self.comments.append(
                        Comment(
                            t.text,
                            first_token=t,
                            last_token=t,
                        )
                    )
                elif t.type == LuaLexer.COMMENT:
                    self.comments.append(
                        Comment(
                            t.text,
                            True,
                            first_token=t,
                            last_token=t,
                        )
                    )
                elif t.type == LuaLexer.NEWLINE:
                    # append n time a None value (indicate newline)
                    self.comments += t.text.count("\n") * [None]

        self._hidden_handled = True

    def get_comments(self) -> Comments:
        comments = [c for c in self.comments if c is not None]
        self.comments = []
        return comments

    def get_comments_followed_by_blank_line(self) -> Comments:
        """Returns comments followed by a blank line."""
        if not self.comments:
            return []

        idx = 0
        comments: List[Comment] = []

        # search first comment
        while idx < len(self.comments) and self.comments[idx] is None:
            idx += 1
        # get comments starting from this index
        while idx < len(self.comments) and self.comments[idx] is not None:
            comments.append(self.comments[idx])
            idx += 1
        # check if followed by a blank line
        if idx + 1 < len(self.comments):
            if self.comments[idx] is None and self.comments[idx + 1] is None:
                # clean list
                self.comments = self.comments[idx + 2:]
                return comments
        return []

    def get_inline_comment(self) -> Comment or None:
        if self.comments:
            c = self.comments.pop(0)
            if c is None:
                return None
            else:
                return c
        return None

    def has_newline_before(self) -> bool:
        return None in self.comments

    def abort(self) -> None:
        types_str = []
        token = self._stream.LT(2)
        expected = set(self._expected)
        for type_to_seek in expected:
            types_str.append(LITERAL_NAMES[type_to_seek])

        raise SyntaxException(
            "Expecting one of "
            + ", ".join(types_str)
            + " at line "
            + str(token.line)
            + ", column "
            + str(token.column)
        )

    def parse_chunk(self) -> Chunk or None:
        first_token: Token = self._stream.LT(1)
        self.handle_hidden_left()
        comments = self.get_comments_followed_by_blank_line()
        block = self.parse_block()
        if block:
            token = self._stream.LT(1)
            if token.type == -1:
                # do not consume EOF
                return Chunk(
                    block,
                    comments=comments,
                    first_token=first_token,
                    last_token=self._LT,
                )
        return False

    def parse_block(self) -> Block:
        t: Token = self._stream.LT(1)
        statements = []

        while True:
            stat = self.parse_stat()
            if not stat:
                break
            statements.append(stat)

        # optional ret stat
        stat = self.parse_ret_stat()
        if stat:
            statements.append(stat)

        # force handle trailing hidden tokens after block
        self._hidden_handled = False
        self.handle_hidden_right()
        return Block(
            statements,
            first_token=t,
            last_token=statements[-1].last_token if statements else None,
            comments=self.get_comments(),
        )

    def parse_stat(self) -> Statement or None:
        comments = self.get_comments()

        stat = (
                self.parse_assignment()
                or self.parse_var(is_statement=True)
                or self.parse_while_stat()
                or self.parse_repeat_stat()
                or self.parse_local()
                or self.parse_goto_stat()
                or self.parse_if_stat()
                or self.parse_for_stat()
                or self.parse_function()
                or self.parse_label()
        )

        if stat:
            stat.comments = comments
            return stat

        stat = self.parse_do_block()
        if stat:
            self.handle_hidden_right()
            return Do(stat)

        if self.next_is(LuaLexer.BREAK) and self.next_is_rc(LuaLexer.BREAK):
            self.handle_hidden_right()
            return Break()
        if self.next_is(LuaLexer.SEMCOL) and self.next_is_rc(LuaLexer.SEMCOL):
            self.handle_hidden_right()
            return SemiColon()

        return None

    def parse_ret_stat(self) -> Return or bool:
        self.save()
        if self.next_is_rc(LuaLexer.RETURN):
            t: Token = self._LT
            expr_list = self.parse_expr_list()  # optional
            # consume optional token
            if self.next_is(LuaLexer.SEMCOL):
                self.next_is_rc(LuaLexer.SEMCOL)

            self.success()
            return Return(expr_list, first_token=t, last_token=self._LT)
        return self.failure()

    def parse_assignment(self) -> Assign or bool:
        self.save()
        t: Token = self._stream.LT(1)
        targets = self.parse_var_list()
        if targets:
            if self.next_is_rc(LuaLexer.ASSIGN):
                values = self.parse_expr_list()
                if values:
                    self.success()
                    return Assign(
                        targets,
                        values,
                        first_token=t,
                        last_token=self._LT,
                    )
                else:
                    self.abort()

        return self.failure()

    def parse_var_list(self) -> List[Expression] or bool:
        lua_vars = []
        self.save()
        var = self.parse_var()
        if var:
            lua_vars.append(var)
            while True:
                self.save()
                if self.next_is_rc(LuaLexer.COMMA):
                    var = self.parse_var()
                    if var:
                        lua_vars.append(var)
                        self.success()
                    else:
                        self.failure()
                        return self.failure()
                else:
                    self.failure()
                    break
            self.success()
            return lua_vars
        return self.failure()

    # When is_statement is true, root must be a Statement.
    def parse_var(self, is_statement=False) -> Node or bool:
        self.save()
        root = self.parse_callee()
        if root:
            tail = self.parse_tail()
            while tail:
                tail.first_token = root.first_token

                if isinstance(tail, Call):
                    tail.func = root
                elif isinstance(tail, Index):
                    tail.value = root
                elif isinstance(tail, Invoke):
                    tail.source = root
                elif isinstance(tail, RequiredField):
                    tail.value = root
                elif isinstance(tail, OptionalField):
                    tail.value = root
                else:
                    args = _listify(tail)
                    tail = Call(
                        root,
                        args,
                        first_token=root.first_token,
                        last_token=args[-1].last_token if args else None,
                    )
                root = tail

                tail = self.parse_tail()
                if tail:
                    self.handle_hidden_right()
            if is_statement and not isinstance(root, Statement):
                return self.failure()
            self.handle_hidden_right()
            self.success()
            return root

        return self.failure()

    def parse_tail(self) -> Node or bool:
        # do not render last hidden
        self.save()
        if self.next_is_rc(LuaLexer.REQFIELD):
            self.success()
            return RequiredField(None)  # value will be set in parent

        if self.next_is_rc(LuaLexer.OPTIONALFIELD):
            self.success()
            return OptionalField(None)  # value will be set in parent

        if self.next_is_rc(LuaLexer.DOT) and self.next_is_rc(LuaLexer.NAME, False):
            self.success()
            return Index(
                Name(
                    self.text,
                    first_token=self._LT,
                    last_token=self._LT,
                ),
                # value must be set in parent
                Name(""),
                last_token=self._LT,
            )

        self.failure_save()
        if self.next_is_rc(LuaLexer.OBRACK):
            expr = self.parse_expr()
            if expr and self.next_is_rc(LuaLexer.CBRACK, False):
                self.success()
                return Index(
                    expr,
                    Name(""),
                    notation=IndexNotation.SQUARE,
                    # value must be set in parent
                )

        self.failure_save()
        if self.next_is_rc(LuaLexer.COL) and self.next_is_rc(LuaLexer.NAME):
            name = Name(
                self.text,
                first_token=self._LT,
                last_token=self._LT,
            )
            if self.next_is_rc(LuaLexer.OPAR):
                expr_list = self.parse_expr_list() or []
                if self._pipe_in_function_call:
                    self._pipe_in_function_call = False
                    self.success()
                    return Invoke(None, name, expr_list)
                elif self.next_is_rc(LuaLexer.CPAR, False):
                    self.success()
                    # noinspection PyTypeChecker
                    return Invoke(None, name, expr_list)

        self.failure_save()
        if self.next_is_rc(LuaLexer.COL) and self.next_is_rc(LuaLexer.NAME):
            name = Name(
                self.text,
                first_token=self._LT,
                last_token=self._LT,
            )
            table = self.parse_table_constructor(False)
            if table:
                self.success()
                # noinspection PyTypeChecker
                return Invoke(None, name, [table])

        self.failure_save()
        if self.next_is_rc(LuaLexer.COL) and self.next_is_rc(LuaLexer.NAME):
            name = Name(
                self.text,
                first_token=self._LT,
                last_token=self._LT,
            )
            if self.next_is_rc(LuaLexer.STRING, False):
                string = self.parse_lua_str(self.text, self._LT)
                self.success()
                # noinspection PyTypeChecker
                return Invoke(None, name, [string])

        self.failure_save()
        if self.next_is(LuaLexer.OPAR):
            # handle the ambiguous syntax
            # http://lua-users.org/lists/lua-l/2009-08/msg00543.html
            # example:
            #   a = b + c;
            #   (print or io.write)('foo')

            # check if a newline is present before OPAR
            tokens = self._stream.getHiddenTokensToLeft(self._stream.index)
            if tokens:
                for t in tokens:
                    if t.type == LuaLexer.NEWLINE and not self.prev_is(LuaLexer.SEMCOL):
                        raise SyntaxException(
                            "Ambiguous syntax detected", self._stream.LT(-1)
                        )
        self.failure_save()
        if self.next_is_rc(LuaLexer.BITOR):
            if self.next_is_rc(LuaLexer.FUNCTION):
                self.handle_hidden_right()
                body = self.parse_func_body()
                if body:
                    self.success()
                    function_arg = Function(None, body[0], body[1])
                    return Call(None, [function_arg], last_token=self._LT)
            elif not self.next_is(LuaLexer.CPAR):
                self.handle_hidden_right()
                expr = self.parse_expr()
                if expr:
                    self.success()
                    return Call(None, expr, last_token=self._LT)

        if self.next_is_rc(LuaLexer.OPAR, False):
            self.handle_hidden_right()
            expr_list = self.parse_expr_list() or []
            if self.next_is_rc(LuaLexer.CPAR, False) or True:
                self.success()
                # noinspection PyTypeChecker
                return Call(None, expr_list, last_token=self._LT)

        self.failure_save()
        table = self.parse_table_constructor(False)
        if table:
            self.success()
            return table

        self.failure_save()
        if self.next_is_rc(LuaLexer.STRING, False):
            string = self.parse_lua_str(self.text, self._LT)
            self.success()
            return string

        return self.failure()

    def parse_expr_list(self) -> List[Expression] or bool:
        expr_list: List[Expression] = []
        self.save()
        expr = self.parse_expr()
        if expr:
            expr_list.append(expr)
            while True:
                self.save()
                if self.next_is_rc(LuaLexer.COMMA):
                    self._expected = []
                    if self.next_is_rc(LuaLexer.BITOR) and self.next_is_rc(LuaLexer.CPAR):
                        expr = self.parse_expr()
                        if expr:
                            expr_list.append(expr)
                            self.success()
                            self._pipe_in_function_call = True
                    else:
                        expr = self.parse_expr()
                        if expr:
                            expr_list.append(expr)
                            self.success()
                        else:
                            # a comma is alone at the end
                            self.failure()
                            self.failure()
                            self.abort()
                else:
                    self.failure()
                    break
            self.success()
            return expr_list
        return self.failure()

    def parse_do_block(self) -> Block or bool:
        self.save()
        if self.next_is_rc(LuaLexer.DO, False):  # or True:
            self.handle_hidden_right()
            block = self.parse_block()
            if block:
                if self.next_is_rc(LuaLexer.END):
                    self.success()
                    return block
        return self.failure()

    def parse_optional_do_block(self) -> Block or bool:
        self.save()
        if self.next_is_rc(LuaLexer.DO, False) or True:
            self.handle_hidden_right()
            block = self.parse_block()
            if block:
                if self.next_is_rc(LuaLexer.END):
                    self.success()
                    return block
        return self.failure()

    def parse_while_stat(self) -> While or bool:
        self.save()
        if self.next_is_rc(LuaLexer.WHILE):
            self._expected = []
            expr = self.parse_expr()
            if expr:
                self._expected = []
                body = self.parse_do_block()
                if body:
                    self.success()
                    return While(expr, body)
            self.abort()

        return self.failure()

    def parse_repeat_stat(self) -> Repeat or bool:
        self.save()
        if self.next_is_rc(LuaLexer.REPEAT, False):
            self.handle_hidden_right()
            body = self.parse_block()
            if body:
                if self.next_is_rc(LuaLexer.UNTIL):
                    expr = self.parse_expr()
                    if expr:
                        self.success()
                        return Repeat(body, expr)

        return self.failure()

    def parse_local(self) -> Node or bool:
        self.save()
        self._expected = []
        start_token = self.next_is_rc(LuaLexer.LOCAL)
        if start_token:
            targets = self.parse_name_list()
            if targets:
                values = []
                self.save()
                if self.next_is_rc(LuaLexer.ASSIGN):
                    values = self.parse_expr_list()
                    if values:
                        self.success()
                    else:
                        self.failure()
                        self.failure()
                        self.abort()
                elif self.next_is_rc(LuaLexer.IN):
                    value = self.parse_names()
                    for target in targets:
                        values.append(
                            Index(
                                target,
                                value,
                                first_token=target.first_token,
                                last_token=target.last_token,
                            )
                        )
                else:
                    self.failure()

                self.success()
                return LocalAssign(
                    targets,
                    values,
                    first_token=start_token,
                    last_token=values[-1].last_token if values else None,
                )

            self.save()

            if self.next_is_rc(LuaLexer.FUNCTION) and self.next_is_rc(LuaLexer.NAME):
                name = Name(
                    self.text,
                    first_token=self._LT,
                    last_token=self._LT,
                )
                body = self.parse_func_body()
                if body:
                    self.success()
                    self.success()
                    node = LocalFunction(name, body[0], body[1])
                    self.handle_hidden_right()
                    node.first_token = start_token
                    node.last_token = body[1].last_token
                    return node
            self.failure()
            self.abort()

        return self.failure()

    def parse_goto_stat(self) -> Goto or bool:
        self.save()
        if self.next_is_rc(LuaLexer.GOTO) and self.next_is_rc(LuaLexer.NAME):
            self.success()
            return Goto(
                Name(
                    self.text,
                    first_token=self._LT,
                    last_token=self._LT,
                )
            )
        return self.failure()

    def parse_if_stat(self) -> If or bool:
        self.save()
        if self.next_is_rc(LuaLexer.IF):
            self._expected = []
            test = self.parse_expr()
            if test:
                if self.next_is_rc(LuaLexer.THEN, False) or True:
                    self.handle_hidden_right()
                    body = self.parse_block()
                    if body:
                        main = If(test, body, None)
                        root = main
                        while True:  # zero or more
                            orelse = self.parse_elseif_stat()
                            if not orelse:
                                break
                            else:
                                root.orelse = orelse
                                root = orelse

                        else_exp = self.parse_else_stat()  # optional
                        if else_exp:
                            root.orelse = else_exp
                        if self.next_is_rc(LuaLexer.END):
                            self.success()
                            return main
                self.abort()
        return self.failure()

    def parse_elseif_stat(self) -> ElseIf or bool:
        self.save()
        if self.next_is_rc(LuaLexer.ELSEIF):
            test = self.parse_expr()
            if test:
                if self.next_is_rc(LuaLexer.THEN, False):
                    self.handle_hidden_right()
                    body = self.parse_block()
                    if body:
                        self.success()
                        return ElseIf(test, body, None)  # orelse will be set in parent
        return self.failure()

    def parse_else_stat(self) -> Block or bool:
        self.save()
        if self.next_is(LuaLexer.ELSE):
            if self.next_is_rc(LuaLexer.ELSE, False):
                self.handle_hidden_right()
                body = self.parse_block()
                if body:
                    self.success()
                    return body
        return self.failure()

    def parse_for_stat(self) -> Fornum or Forin or bool:
        self.save()
        if self.next_is_rc(LuaLexer.FOR):
            self.save()
            if self.next_is_rc(LuaLexer.NAME):
                target = Name(
                    self.text,
                    first_token=self._LT,
                    last_token=self._LT,
                )
                if self.next_is_rc(LuaLexer.ASSIGN):
                    start = self.parse_expr()
                    if start and self.next_is_rc(LuaLexer.COMMA):
                        stop = self.parse_expr()
                        if stop:
                            step = 1
                            # optional step
                            if self.next_is(LuaLexer.COMMA) and self.next_is_rc(
                                    LuaLexer.COMMA
                            ):
                                step = self.parse_expr()

                            body = self.parse_optional_do_block()
                            if not body:
                                self.failure()
                                return self.failure()
                            self.success()
                            self.success()
                            return Fornum(target, start, stop, step, body)

            self.failure_save()
            target = self.parse_name_list()
            if target:
                if self.next_is_rc(LuaLexer.IN):
                    iter_expr = self.parse_expr_list()
                    if iter_expr:
                        body = self.parse_optional_do_block()
                        if body:
                            self.success()
                            self.success()
                            return Forin(body, iter_expr, target)
                elif self.next_is_rc(LuaLexer.SEMCOL):
                    iter_expr = self.parse_expr_list()
                    if iter_expr:
                        first_expr = iter_expr[0]
                        replace_expr = Call(
                            Name("pairs"),
                            [first_expr],
                            first_token=first_expr.first_token,
                            last_token=first_expr.last_token,
                        )
                        body = self.parse_optional_do_block()
                        if body:
                            self.success()
                            self.success()
                            return Forin(body, [replace_expr], target)

            self.failure()

        return self.failure()

    def parse_function(self) -> Method or Function or bool:
        self.save()
        self._expected = []
        start_token = self.next_is_rc(LuaLexer.FUNCTION)
        if start_token:
            names = self.parse_names()
            if names:
                self.save()
                if self.next_is_rc(LuaLexer.COL) and self.next_is_rc(LuaLexer.NAME):
                    name = Name(
                        self.text,
                        first_token=self._LT,
                        last_token=self._LT,
                    )
                    func_body = self.parse_func_body()
                    if func_body:
                        self.success()
                        self.success()
                        node = Method(
                            names,
                            name,
                            func_body[0],
                            func_body[1],
                            first_token=start_token,
                            last_token=func_body[1].last_token,
                        )
                        self.handle_hidden_right()
                        return node

                self.failure()

                func_body = self.parse_func_body()
                if func_body:
                    self.success()
                    node = Function(
                        names,
                        func_body[0],
                        func_body[1],
                        first_token=start_token,
                        last_token=func_body[1].last_token,
                    )
                    self.handle_hidden_right()
                    return node
            self.abort()

        return self.failure()

    def parse_names(self) -> Name or Index or bool:
        self.save()
        if self.next_is_rc(LuaLexer.NAME):
            root = Name(
                self.text,
                first_token=self._LT,
                last_token=self._LT,
            )
            while True:
                self.save()
                if self.next_is_rc(LuaLexer.DOT) and self.next_is_rc(LuaLexer.NAME):
                    self.success()
                    child = Index(
                        Name(
                            self.text,
                            first_token=self._LT,
                            last_token=self._LT,
                        ),
                        root,
                    )
                    root = child
                else:
                    self.failure()
                    break
            self.success()
            return root
        self.failure()

    def parse_func_body(self):
        """If success, return a tuple (args, body)"""
        self.save()
        self._expected = []
        if self.next_is_rc(LuaLexer.OPAR, False):  # do not render right hidden
            self.handle_hidden_right()  # render hidden bases after new level
            args = self.parse_param_list()
            if args is not None:  # may be an empty table
                if self.next_is_rc(LuaLexer.CPAR, False):  # do not render right hidden
                    self.handle_hidden_right()  # render hidden after new level
                    body = self.parse_block()
                    if body:
                        self._expected = []
                        token = self.next_is_rc(LuaLexer.END, False)
                        if token:
                            body.last_token = token
                            self.success()
                            return args, body
                        else:
                            self.abort()
                else:
                    self.abort()
        return self.failure()

    def parse_param_list(self) -> List[Expression] or bool:
        param_list: List[Expression] = self.parse_name_list()
        if param_list:
            self.save()
            if self.next_is_rc(LuaLexer.COMMA) and self.next_is_rc(LuaLexer.VARARGS):
                self.success()
                param_list.append(Varargs())
                return param_list
            else:
                self.failure()
                return param_list

        self.save()
        if self.next_is_rc(LuaLexer.VARARGS):
            self.success()
            return [Varargs()]

        self.success()
        return []

    def parse_name_list(self) -> List[Name] or bool:
        self.save()
        names: List[Name] = []
        if self.next_is_rc(LuaLexer.NAME):
            names.append(
                Name(
                    self.text,
                    first_token=self._LT,
                    last_token=self._LT,
                )
            )
            while True:
                self.save()
                if self.next_is_rc(LuaLexer.COMMA) and self.next_is_rc(LuaLexer.NAME):
                    names.append(
                        Name(
                            self.text,
                            first_token=self._LT,
                            last_token=self._LT,
                        )
                    )
                    self.success()
                else:
                    self.failure()
                    break
            self.success()
            return names
        return self.failure()

    def parse_label(self) -> Label or bool:
        self.save()
        if self.next_is_rc(LuaLexer.COLCOL) and self.next_is_rc(LuaLexer.NAME):
            name = Name(
                self.text,
                first_token=self._LT,
                last_token=self._LT,
            )
            if self.next_is_rc(LuaLexer.COLCOL):
                self.success()
                return Label(name)

        return self.failure()

    def parse_callee(self) -> Expression or bool:
        self.save()
        if self.next_is_rc(LuaLexer.OPAR):
            expr = self.parse_expr()
            if expr:
                if self.next_is_rc(LuaLexer.CPAR):
                    self.success()
                    expr.wrapped = True
                    return expr
        self.failure()
        self.save()
        if self.next_is_rc(LuaLexer.CONCAT):
            if self.next_is_rc(LuaLexer.NAME):
                self.success()
                return StringifiedName(
                    self.text,
                    first_token=self._LT,
                    last_token=self._LT,
                )
        if self.next_is_rc(LuaLexer.NAME):
            self.success()
            return Name(
                self.text,
                first_token=self._LT,
                last_token=self._LT,
            )
        return self.failure()

    def parse_expr(self) -> Expression or bool:
        return self.parse_or_expr()

    def parse_or_expr(self) -> Expression or Literal[False]:
        self.save()
        left = self.parse_and_expr()
        if left:
            while True:
                self.save()
                if self.next_is_rc(LuaLexer.OR):
                    right = self.parse_and_expr()
                    if right:
                        self.success()
                        left = OrLoOp(left, right)
                    else:
                        self.failure()
                        return self.failure()
                else:
                    self.failure()
                    break
            self.success()
            return left

        return self.failure()

    def parse_and_expr(self) -> Expression or bool:
        self.save()
        left = self.parse_rel_expr()
        if left:
            while True:
                self.save()
                if self.next_is_rc(LuaLexer.AND):
                    right = self.parse_rel_expr()
                    if right:
                        self.success()
                        left = AndLoOp(left, right)
                    else:
                        self.failure()
                        return self.failure()
                else:
                    self.failure()
                    break
            self.success()
            return left

        return self.failure()

    def parse_rel_expr(self) -> Expression or bool:
        self.save()
        left = self.parse_concat_expr()
        if left:
            self.save()
            if self.next_in_rc(self.REL_OPERATORS):
                op = self.type
                right = self.parse_concat_expr()
                if right:
                    self.success()
                    if op == LuaLexer.LT:
                        left = LessThanOp(left, right)
                    elif op == LuaLexer.GT:
                        left = GreaterThanOp(left, right)
                    elif op == LuaLexer.LTEQ:
                        left = LessOrEqThanOp(left, right)
                    elif op == LuaLexer.GTEQ:
                        left = GreaterOrEqThanOp(left, right)
                    elif op == LuaLexer.NEQ:
                        left = NotEqToOp(left, right)
                    elif op == LuaLexer.EQ:
                        left = EqToOp(left, right)
                else:
                    self.failure()
                    return self.failure()
            else:
                self.failure()
            self.success()
            return left
        return self.failure()

    def parse_concat_expr(self) -> Expression or bool:
        self.save()
        left = self.parse_add_expr()
        if left:
            while True:
                self.save()
                if self.next_is_rc(LuaLexer.CONCAT):
                    self._expected = []
                    right = self.parse_add_expr()
                    if right:
                        self.success()
                        left = Concat(left, right)
                    else:
                        self.failure()
                        self.failure()
                        self.abort()
                else:
                    self.failure()
                    break
            self.success()
            return left

        return self.failure()

    def parse_add_expr(self) -> Expression or bool:
        self.save()
        left = self.parse_mult_expr()
        if left:
            while True:
                self.save()
                if self.next_in_rc([LuaLexer.ADD, LuaLexer.MINUS]):
                    op = self.type
                    right = self.parse_mult_expr()
                    if right:
                        self.success()
                        if op == LuaLexer.ADD:
                            left = AddOp(left, right)
                        elif op == LuaLexer.MINUS:
                            left = SubOp(left, right)
                    else:
                        self.failure()
                        return self.failure()
                else:
                    self.failure()
                    break
            self.success()
            return left

        return self.failure()

    def parse_mult_expr(self) -> Expression or bool:
        self.save()
        left = self.parse_bitwise_expr()
        if left:
            while True:
                self.save()
                if self.next_in_rc([LuaLexer.MULT, LuaLexer.DIV, LuaLexer.MOD, LuaLexer.FLOOR]):
                    op = self.type
                    right = self.parse_bitwise_expr()
                    if right:
                        self.success()
                        if op == LuaLexer.MULT:
                            left = MultOp(left, right)
                        elif op == LuaLexer.DIV:
                            left = FloatDivOp(left, right)
                        elif op == LuaLexer.MOD:
                            left = ModOp(left, right)
                        elif op == LuaLexer.FLOOR:
                            left = FloorDivOp(left, right)
                    else:
                        self.failure()
                        return self.failure()
                else:
                    self.failure()
                    break
            self.success()
            return left

        return self.failure()

    def parse_bitwise_expr(self) -> Expression or bool:
        self.save()
        left = self.parse_unary_expr()
        if left:
            while True:
                self.save()
                if self.next_in_rc(
                        [
                            LuaLexer.BITAND,
                            LuaLexer.BITOR,
                            LuaLexer.BITNOT,
                            LuaLexer.BITRSHIFT,
                            LuaLexer.BITRLEFT,
                        ]
                ):
                    op = self.type
                    right = self.parse_unary_expr()
                    if right:
                        self.success()
                        if op == LuaLexer.BITAND:
                            left = BAndOp(left, right)
                        elif op == LuaLexer.BITOR:
                            left = BOrOp(left, right)
                        elif op == LuaLexer.BITNOT:
                            left = BXorOp(left, right)
                        elif op == LuaLexer.BITRSHIFT:
                            left = BShiftROp(left, right)
                        elif op == LuaLexer.BITRLEFT:
                            left = BShiftLOp(left, right)
                    else:
                        self.failure()
                        return self.failure()
                else:
                    self.failure()
                    break
            self.success()
            return left

        return self.failure()

    def parse_unary_expr(self) -> Expression or bool:
        self.save()
        if self.next_is_rc(LuaLexer.MINUS):
            t: Token = self._LT
            expr = self.parse_unary_expr()
            if expr:
                self.success()
                return UMinusOp(expr, first_token=t, last_token=t)

        self.failure_save()
        if self.next_is_rc(LuaLexer.LENGTH):
            t: Token = self._LT
            expr = self.parse_expr()
            if expr:
                self.success()
                return ULengthOP(expr, first_token=t, last_token=t)

        self.failure_save()
        if self.next_is_rc(LuaLexer.NOT):
            t: Token = self._LT
            expr = self.parse_unary_expr()
            if expr:
                self.success()
                return ULNotOp(expr, first_token=t, last_token=t)

        self.failure_save()
        if self.next_is_rc(LuaLexer.BITNOT):
            t: Token = self._LT
            expr = self.parse_unary_expr()
            if expr:
                self.success()
                return UBNotOp(expr, first_token=t, last_token=t)

        self.failure_save()
        expr = self.parse_pow_expr()
        if expr:
            self.success()
            return expr

        return self.failure()

    def parse_pow_expr(self) -> Expression or bool:
        self.save()
        left = self.parse_atom()
        if left:
            while True:
                self.save()
                if self.next_is_rc(LuaLexer.POW):
                    right = self.parse_expr()
                    if right:
                        self.success()
                        left = ExpoOp(left, right)
                    else:
                        self.failure()
                        return self.failure()
                else:
                    self.failure()
                    break
            self.success()
            return left

        self.failure()

    def parse_atom(self) -> Expression or bool:
        atom = self.parse_var()
        if atom:
            return atom
        atom = self.parse_function_literal()
        if atom:
            return atom
        atom = self.parse_table_constructor()
        if atom:
            return atom
        if self.next_is(LuaLexer.VARARGS) and self.next_is_rc(LuaLexer.VARARGS):
            return Varargs()

        if self.next_is(LuaLexer.NUMBER) and self.next_is_rc(LuaLexer.NUMBER):
            # TODO: optimize
            # using python number eval to parse lua number
            try:
                number = ast.literal_eval(self.text)
            except:
                # exception occurs with leading zero number: 002
                number = float(self.text)
            return Number(
                number,
                first_token=self._LT,
                last_token=self._LT,
            )

        if self.next_is(LuaLexer.STRING) and self.next_is_rc(LuaLexer.STRING):
            string = self.parse_lua_str(self.text, self._LT)
            return string

        if self.next_is(LuaLexer.NIL) and self.next_is_rc(LuaLexer.NIL):
            return Nil(first_token=self._LT, last_token=self._LT)

        if self.next_is(LuaLexer.TRUE) and self.next_is_rc(LuaLexer.TRUE):
            return TrueExpr(first_token=self._LT, last_token=self._LT)

        if self.next_is(LuaLexer.FALSE) and self.next_is_rc(LuaLexer.FALSE):
            return FalseExpr(first_token=self._LT, last_token=self._LT)
        return None

    @staticmethod
    def parse_lua_str(lua_str, token: Optional[CommonToken] = None) -> String:
        delimiter: StringDelimiter = StringDelimiter.SINGLE_QUOTE
        p = re.compile(r"^\[=+\[(.*)]=+]")  # nested quote pattern
        # try remove double quote:
        if lua_str.startswith('"') and lua_str.endswith('"'):
            lua_str = lua_str[1:-1]
            delimiter = StringDelimiter.DOUBLE_QUOTE
        # try remove single quote:
        elif lua_str.startswith("'") and lua_str.endswith("'"):
            lua_str = lua_str[1:-1]
            delimiter = StringDelimiter.SINGLE_QUOTE
        # try remove double square bracket:
        elif lua_str.startswith("[[") and lua_str.endswith("]]"):
            lua_str = lua_str[2:-2]
            delimiter = StringDelimiter.DOUBLE_SQUARE
        # nested quote
        elif p.match(lua_str):
            lua_str = p.search(lua_str).group(1)
        return String(lua_str, delimiter, first_token=token, last_token=token)

    def parse_function_literal(self) -> AnonymousFunction or bool:
        self.save()
        if self.next_is_rc(LuaLexer.FUNCTION):
            t: Token = self._LT
            func_body = self.parse_func_body()
            if func_body:
                self.success()
                node = AnonymousFunction(
                    func_body[0],
                    func_body[1],
                    first_token=t,
                    last_token=self._LT,
                )
                self.handle_hidden_right()
                return node

        return self.failure()

    def parse_table_constructor(self, render_last_hidden=True) -> Table or bool:
        self.save()
        if self.next_is_rc(LuaLexer.OBRACE, False):  # do not render right hidden
            self.handle_hidden_right()  # render hidden after new level

            fields = self.parse_field_list()
            if self.next_is_rc(LuaLexer.CBRACE, render_last_hidden):
                self.success()

                array_like_index = 1
                if fields:  # optional
                    for field in fields:
                        if field.key is None:
                            field.key = Number(array_like_index)
                            field.between_brackets = True
                            array_like_index += 1

                return Table(fields or [])

        return self.failure()

    def parse_field_list(self) -> List[Field] or bool:
        field_list = []
        self.save()
        field, _ = self.parse_field()
        if field:
            field_list.append(field)
            while True:
                self.save()
                if self.next_in_rc([LuaLexer.COMMA, LuaLexer.SEMCOL]):
                    inline_com = self.get_inline_comment()
                    if inline_com:
                        field.comments.append(inline_com)
                    prev_field = field
                    field, remaining_comments = self.parse_field()
                    if field:
                        field_list.append(field)
                        self.success()
                    else:
                        prev_field.comments.extend(remaining_comments)
                        self.success()
                        self.success()
                        return field_list
                else:
                    field.comments.extend(self.get_comments())
                    self.failure()
                    break
            self.parse_field_sep()
            self.success()
            return field_list
        return self.failure()

    def parse_field(self) -> Tuple[Field or bool, Comments]:
        self.save()

        if self.next_is_rc(LuaLexer.OBRACK):
            key = self.parse_expr()
            if key and self.next_is_rc(LuaLexer.CBRACK):
                if self.next_is_rc(LuaLexer.ASSIGN):
                    comments = self.get_comments()
                    value = self.parse_expr()
                    if value:
                        self.success()
                        return (
                            Field(key, value, comments=comments, between_brackets=True),
                            comments,
                        )

        self.failure_save()
        if self.next_is_rc(LuaLexer.CONCAT):
            comments = self.get_comments()
            value = self.parse_expr()
            if value:
                if isinstance(value, Name):
                    self.success()
                    return Field(value, value, comments=comments), comments
                elif isinstance(value, Index):
                    self.success()
                    return Field(value.idx, value, comments=comments), comments

        if self.next_is_rc(LuaLexer.NAME):
            key = Name(
                self.text,
                first_token=self._LT,
                last_token=self._LT,
            )
            if self.next_is_rc(LuaLexer.ASSIGN):
                comments = self.get_comments()
                value = self.parse_expr()
                if value:
                    self.success()
                    return Field(key, value, comments=comments), comments

        self.failure_save()
        comments = self.get_comments()
        value = self.parse_expr()
        if value:
            self.success()
            # noinspection PyTypeChecker
            return (
                Field(None, value, comments=comments),
                [],
            )  # Key will be set in parse_table_constructor

        return self.failure(), comments

    def parse_field_sep(self) -> bool:
        self.save()
        if self.next_in_rc([LuaLexer.COMMA, LuaLexer.SEMCOL]):
            return self.success()
        return self.failure()

#don't touch the pipes!