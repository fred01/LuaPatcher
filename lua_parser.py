from antlr4 import *
from gen import LuaLexer
from gen.LuaParser import LuaParser
from gen.LuaParserVisitor import LuaParserVisitor
from gen.LuaParserListener import LuaParserListener

from luaparser.astnodes import *


class Eq:
    pass

class Pipe:
    pass

class Eof:
    pass

class Comma():
    pass

class MyLuaParserVisitor(LuaParserVisitor):

    def split_list(self, lst, splitter):
        if any(isinstance(i, splitter) for i in lst):
            index = next(i for i, x in enumerate(lst) if isinstance(x, Pipe))
            return lst[:index], lst[index + 1:]
        else:
            return None

    def defaultResult(self):
        return None

    def aggregateResult(self, aggregate, nextResult):
        if isinstance(aggregate, list):
            aggregate.append(nextResult)
            return aggregate
        if aggregate is None:
            return nextResult
        else:
            return [aggregate, nextResult]

    def visitChunk(self, ctx: LuaParser.ChunkContext):
        print("visitChunk")
        block = self.visitChildren(ctx)
        print(block)

    def visitBlock(self, ctx: LuaParser.BlockContext):
        print("visitBlock")
        a = self.visitChildren(ctx)
        print(a)
        return Block([])

    def visitStat(self, ctx: LuaParser.StatContext):
        print("visitStat")
        stat = self.visitChildren(ctx)
        # print(stat)
        return stat

    def visitVarlist(self, ctx: LuaParser.VarlistContext):
        print("visitVarlist")
        var_list = self.visitChildren(ctx)
        # print(var_list)
        return var_list

    def visitVar(self, ctx: LuaParser.VarContext):
        print("visitVar")
        return self.visitChildren(ctx)

    def visitExplist(self, ctx: LuaParser.ExplistContext):
        print("visitExplist")
        exp_list = self.visitChildren(ctx)
        # print(exp_list)
        return exp_list

    def visitExp(self, ctx:LuaParser.ExpContext):
        return self.visitChildren(ctx)


    def visitString(self, ctx: LuaParser.StringContext):
        s = self.visitChildren(ctx)
        return String(s)

    def visitFunctioncall(self, ctx:LuaParser.FunctioncallContext):
        call = self.visitChildren(ctx)

        split = self.split_list(call, Pipe)
        if split:
            return Call(split[0][0], split[1])
        else:
            raise Exception("Invalid call")


    def visitTerminal(self, node):
        token: Token = node.getSymbol()
        if token.type == LuaParser.NAME:
            return Name(token.text)
        elif token.type == LuaParser.NORMALSTRING:
            return String(token.text)
        elif token.type == LuaParser.EQ:
            return Eq()
        elif token.type == LuaParser.PIPE:
            return Pipe()
        elif token.type == LuaParser.EOF:
            return Eof()
        elif token.type == LuaParser.COMMA:
            return Comma()
        elif token.type == LuaParser.INT:
            return Number(token.text)

        else:
            raise Exception("Unknown token type: " + str(token.type))




def main():
    input = InputStream("""
      a, b = "Hello World!", 10
      push | a
    """)

    lexer = LuaLexer.LuaLexer(input)
    stream = CommonTokenStream(lexer)
    parser = LuaParser(stream)
    tree = parser.start_()
    print(tree.toStringTree(recog=parser))

    visitor = MyLuaParserVisitor()
    visitor.visit(tree)

    # printer = BuilderNodeListener()
    # walker = ParseTreeWalker()
    # walker.walk(printer, tree)


if __name__ == '__main__':
    main()

# (chunk (block (stat (var (callee push) (tail ( (expr_list (expr (or_expr (and_expr (rel_expr (concat_expr (add_expr (mult_expr (bitwise_expr (unary_expr (pow_expr (atom (var (callee some_value)))))))))))))) ))))) <EOF>)
# (chunk (block (stat (var (callee push) (tail | (expr (or_expr (and_expr (rel_expr (concat_expr (add_expr (mult_expr (bitwise_expr (unary_expr (pow_expr (atom (var (callee some_value))))))))))))))))) <EOF>)
