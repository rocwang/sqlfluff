"""The DuckDB dialect.

https://duckdb.org/docs/
"""

from sqlfluff.core.dialects import load_raw_dialect
from sqlfluff.core.parser import (
    BaseSegment,
    BinaryOperatorSegment,
    Bracketed,
    CodeSegment,
    Dedent,
    Delimited,
    Indent,
    Matchable,
    OneOf,
    OptionallyBracketed,
    Ref,
    Sequence,
    StringLexer,
    StringParser,
)
from sqlfluff.dialects import dialect_ansi as ansi

ansi_dialect = load_raw_dialect("ansi")
postgres_dialect = load_raw_dialect("postgres")
duckdb_dialect = postgres_dialect.copy_as("duckdb")

duckdb_dialect.replace(
    SingleIdentifierGrammar=OneOf(
        Ref("NakedIdentifierSegment"),
        Ref("QuotedIdentifierSegment"),
        Ref("SingleQuotedIdentifierSegment"),
    ),
    DivideSegment=OneOf(
        StringParser("//", BinaryOperatorSegment),
        StringParser("/", BinaryOperatorSegment),
    ),
    UnionGrammar=ansi_dialect.get_grammar("UnionGrammar").copy(
        insert=[
            Sequence("BY", "NAME", optional=True),
        ]
    ),
)

duckdb_dialect.insert_lexer_matchers(
    [
        StringLexer("double_divide", "//", CodeSegment),
    ],
    before="divide",
)


class SelectClauseElementSegment(ansi.SelectClauseElementSegment):
    """An element in the targets of a select statement."""

    type = "select_clause_element"

    match_grammar = OneOf(
        Sequence(
            Ref("WildcardExpressionSegment"),
            OneOf(
                Sequence(
                    "EXCLUDE",
                    OneOf(
                        Ref("ColumnReferenceSegment"),
                        Bracketed(Delimited(Ref("ColumnReferenceSegment"))),
                    ),
                ),
                Sequence(
                    "REPLACE",
                    Bracketed(
                        Delimited(
                            Sequence(
                                Ref("BaseExpressionElementGrammar"),
                                Ref("AliasExpressionSegment", optional=True),
                            ),
                        )
                    ),
                ),
                optional=True,
            ),
        ),
        Sequence(
            Ref("BaseExpressionElementGrammar"),
            Ref("AliasExpressionSegment", optional=True),
        ),
    )


class SelectStatementSegment(ansi.SelectStatementSegment):
    """A duckdb `SELECT` statement including optional Qualify.

    https://duckdb.org/docs/sql/query_syntax/qualify
    """

    type = "select_statement"

    match_grammar = ansi.SelectStatementSegment.match_grammar.copy(
        insert=[Ref("QualifyClauseSegment", optional=True)],
        before=Ref("OrderByClauseSegment", optional=True),
    )


class UnorderedSelectStatementSegment(ansi.UnorderedSelectStatementSegment):
    """A `SELECT` statement without any ORDER clauses or later.

    This is designed for use in the context of set operations,
    for other use cases, we should use the main
    SelectStatementSegment.
    """

    type = "select_statement"

    match_grammar: Matchable = Sequence(
        OneOf(
            Sequence(
                Ref("SelectClauseSegment"),
                Ref("FromClauseSegment", optional=True),
            ),
            Sequence(
                # From-First Syntax:
                # https://duckdb.org/docs/sql/query_syntax/from
                Ref("FromClauseSegment"),
                Ref("SelectClauseSegment", optional=True),
            ),
        ),
        Ref("WhereClauseSegment", optional=True),
        Ref("GroupByClauseSegment", optional=True),
        Ref("HavingClauseSegment", optional=True),
        Ref("NamedWindowSegment", optional=True),
        Ref("QualifyClauseSegment", optional=True),
        terminators=[
            Ref("SetOperatorSegment"),
            Ref("OrderByClauseSegment"),
            Ref("LimitClauseSegment"),
        ],
    )


class OrderByClauseSegment(ansi.OrderByClauseSegment):
    """A `ORDER BY` clause like in `SELECT`."""

    match_grammar: Matchable = Sequence(
        "ORDER",
        "BY",
        Indent,
        Delimited(
            Sequence(
                OneOf(
                    "ALL",
                    Ref("ColumnReferenceSegment"),
                    Ref("NumericLiteralSegment"),
                    Ref("ExpressionSegment"),
                ),
                OneOf("ASC", "DESC", optional=True),
                Sequence("NULLS", OneOf("FIRST", "LAST"), optional=True),
            ),
            allow_trailing=True,
            terminators=[Ref("OrderByClauseTerminators")],
        ),
        Dedent,
    )


class GroupByClauseSegment(ansi.GroupByClauseSegment):
    """A `GROUP BY` clause like in `SELECT`."""

    match_grammar: Matchable = Sequence(
        "GROUP",
        "BY",
        Indent,
        Delimited(
            OneOf(
                "ALL",
                Ref("ColumnReferenceSegment"),
                Ref("NumericLiteralSegment"),
                Ref("ExpressionSegment"),
            ),
            allow_trailing=True,
            terminators=[Ref("GroupByClauseTerminatorGrammar")],
        ),
        Dedent,
    )


class QualifyClauseSegment(BaseSegment):
    """A `QUALIFY` clause like in `SELECT`.

    https://duckdb.org/docs/sql/query_syntax/qualify.html
    """

    type = "qualify_clause"
    match_grammar = Sequence(
        "QUALIFY",
        Indent,
        OptionallyBracketed(Ref("ExpressionSegment")),
        Dedent,
    )


class ObjectLiteralElementSegment(ansi.ObjectLiteralElementSegment):
    """An object literal element segment."""

    match_grammar: Matchable = Sequence(
        OneOf(
            Ref("NakedIdentifierSegment"),
            Ref("QuotedLiteralSegment"),
        ),
        Ref("ColonSegment"),
        Ref("BaseExpressionElementGrammar"),
    )
