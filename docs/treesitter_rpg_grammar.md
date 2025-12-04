Here’s a starter Tree‑sitter grammar for **IBM ILE RPG free‑form** (aka RPGLE, “all free”).

It focuses on:

* `**FREE` style fully free‑form code([IBM][1])
* `ctl-opt`, `dcl-*` definitions (C/S/DS/F/PR/PI/PARM/SUBF/PROC)([IBM][2])
* Structured control flow: `if / elseif / else / endif`, `dow/dou/do/enddo`, `for/endfor`, `select/when/other/endsl`, `monitor/on-error/endmon`([CertLibrary][3])

It **does not** try to handle old fixed‑format H/F/D/I/C/O/P specs or embedded SQL; you’d need extra work (often a separate “fixed‑form” mode) for that.([IBM][4])

---

### `grammar.js`

Save this as `grammar.js` in a Tree‑sitter language repo (for example `tree-sitter-rpg`):

```javascript
// Tree-sitter grammar for IBM ILE RPG (fully free-form)
// NOTE: This is a reasonably complete starter grammar, not a full spec.
// You will likely extend it for your own codebase.

function escapeRegex(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// Case-insensitive keyword helper, e.g. ci("dcl-s") matches DCL-S, dcl-s, Dcl-S, etc.
function ci(keyword) {
  const escaped = escapeRegex(keyword);
  let pattern = '';
  for (const ch of escaped) {
    if (/[a-zA-Z]/.test(ch)) {
      pattern += `[${ch.toLowerCase()}${ch.toUpperCase()}]`;
    } else {
      pattern += ch;
    }
  }
  return new RegExp(pattern);
}

function sep1(rule, separator) {
  return seq(rule, repeat(seq(separator, rule)));
}

module.exports = grammar({
  name: 'rpg',

  extras: $ => [
    /\s/,        // whitespace (includes newlines, tabs, etc.)
    $.comment,
  ],

  // For editor word-based queries
  word: $ => $.identifier,

  rules: {
    // ------------------------------------------------------------------
    // Top-level
    // ------------------------------------------------------------------
    source_file: $ => repeat($.top_level_item),

    top_level_item: $ => choice(
      $.procedure_definition,
      $.statement
    ),

    // ------------------------------------------------------------------
    // Generic statements
    // ------------------------------------------------------------------
    statement: $ => choice(
      $.ctl_opt,
      $.definition,
      $.if_statement,
      $.select_statement,
      $.loop_statement,
      $.monitor_statement,
      $.return_statement,
      $.preprocessor_directive,
      $.expression_statement
    ),

    expression_statement: $ => seq(
      optional($.expression),
      ';'
    ),

    ctl_opt: $ => seq(
      ci('ctl-opt'),
      // treat everything up to the semicolon as expressions/clauses
      repeat1($.expression),
      ';'
    ),

    // /IF, /ELSE, /ENDIF, /COPY, /INCLUDE, etc.
    preprocessor_directive: $ => token(
      seq('/', /[A-Za-z]+/, /[^\n]*/)
    ),

    // ------------------------------------------------------------------
    // Definitions (DCL-*)
    // ------------------------------------------------------------------
    definition: $ => choice(
      $.dcl_s,
      $.constant_definition,
      $.data_structure_definition,
      $.file_definition,
      $.procedure_prototype,
      $.procedure_interface,
      $.parameter_definition,
      $.subfield_definition
    ),

    // DCL-S salary packed(7:2) inz(0);
    dcl_s: $ => seq(
      ci('dcl-s'),
      field('name', $.identifier_or_star),
      optional($.type_spec),
      repeat($.attribute),
      ';'
    ),

    // DCL-C Pi 3.14159;
    constant_definition: $ => seq(
      ci('dcl-c'),
      field('name', $.identifier_or_star),
      optional($.type_spec),
      field('value', $.expression),
      repeat($.attribute),
      ';'
    ),

    // DCL-DS myDS qualified;
    //   DCL-SUBF field1 char(10);
    // END-DS myDS;
    data_structure_definition: $ => seq(
      ci('dcl-ds'),
      field('name', $.identifier_or_star),
      repeat($.attribute),
      ';',
      repeat(choice(
        $.subfield_definition,
        $.definition,
        $.statement
      )),
      ci('end-ds'),
      optional(field('end_name', $.identifier_or_star)),
      ';'
    ),

    // DCL-SUBF city char(20);
    subfield_definition: $ => seq(
      ci('dcl-subf'),
      field('name', $.identifier_or_star),
      optional($.type_spec),
      repeat($.attribute),
      ';'
    ),

    // DCL-F CustFile usage(*update) extfile(custFileName);
    file_definition: $ => seq(
      ci('dcl-f'),
      field('name', $.identifier),
      repeat($.attribute),
      ';'
    ),

    // DCL-PR AdjustItem extpgm('ADJITEM');
    //   DCL-PARM inItemNo   char(15) const;
    // END-PR AdjustItem;
    procedure_prototype: $ => seq(
      ci('dcl-pr'),
      field('name', $.identifier_or_star),
      optional($.type_spec),        // return type, e.g. ind
      repeat($.attribute),          // extpgm, extproc, export, etc.
      ';',
      repeat($.parameter_definition),
      ci('end-pr'),
      optional(field('end_name', $.identifier_or_star)),
      ';'
    ),

    // DCL-PI *n ind;
    //   DCL-PARM inItemNo char(15) const;
    // END-PI;
    procedure_interface: $ => seq(
      ci('dcl-pi'),
      field('name', $.identifier_or_star),
      optional($.type_spec),
      repeat($.attribute),
      ';',
      repeat($.parameter_definition),
      ci('end-pi'),
      optional(field('end_name', $.identifier_or_star)),
      ';'
    ),

    // DCL-PARM inItemNo char(15) const;
    parameter_definition: $ => seq(
      ci('dcl-parm'),
      field('name', $.identifier_or_star),
      $.type_spec,
      repeat($.attribute),
      ';'
    ),

    // <type> [ ( args... ) ]
    // e.g. packed(7:2), char(20), like(OtherField)
    type_spec: $ => seq(
      field('type', $.identifier),
      optional(seq(
        '(',
        sep1($.expression, choice(',', ':')),
        ')'
      ))
    ),

    // Generic keyword(args...) attributes:
    //   usage(*update)  extpgm('QCMDEXC')  dim(10)  template  const
    attribute: $ => seq(
      choice($.identifier, $.special_identifier),
      optional(seq(
        '(',
        sep1($.expression, choice(',', ':')),
        ')'
      ))
    ),

    // ------------------------------------------------------------------
    // Procedures (DCL-PROC ... END-PROC)
    // ------------------------------------------------------------------
    // DCL-PROC AdjustItem export;
    //   DCL-PI *n;
    //   ...
    //   END-PI;
    //   ...
    // END-PROC AdjustItem;
    procedure_definition: $ => seq(
      ci('dcl-proc'),
      field('name', $.identifier),
      optional($.type_spec),    // return type
      repeat($.attribute),      // export, options, etc.
      ';',
      repeat($.statement),
      ci('end-proc'),
      optional(field('end_name', $.identifier)),
      ';'
    ),

    // ------------------------------------------------------------------
    // Control flow
    // ------------------------------------------------------------------
    // IF cond;
    //   ...
    // ELSEIF cond;
    //   ...
    // ELSE;
    //   ...
    // ENDIF;
    if_statement: $ => seq(
      ci('if'),
      field('condition', $.expression),
      ';',
      repeat($.statement),
      repeat($.elseif_clause),
      optional($.else_clause),
      ci('endif'),
      ';'
    ),

    elseif_clause: $ => seq(
      ci('elseif'),
      field('condition', $.expression),
      ';',
      repeat($.statement)
    ),

    else_clause: $ => seq(
      ci('else'),
      ';',
      repeat($.statement)
    ),

    // SELECT [expr];
    //   WHEN expr;
    //     ...
    //   OTHER;
    //     ...
    // ENDSL;
    select_statement: $ => seq(
      ci('select'),
      optional($.expression),  // operand for WHEN-IS / WHEN-IN
      ';',
      repeat($.when_clause),
      optional($.other_clause),
      ci('endsl'),
      ';'
    ),

    when_clause: $ => seq(
      choice(
        ci('when'),
        ci('when-in'),
        ci('when-is')
      ),
      $.expression,
      ';',
      repeat($.statement)
    ),

    other_clause: $ => seq(
      ci('other'),
      ';',
      repeat($.statement)
    ),

    // DOW / DOU / DO / FOR loops
    loop_statement: $ => choice(
      $.dow_loop,
      $.dou_loop,
      $.do_loop,
      $.for_loop
    ),

    // DOW condition; ... ENDDO;
    dow_loop: $ => seq(
      ci('dow'),
      $.expression,
      ';',
      repeat($.statement),
      ci('enddo'),
      ';'
    ),

    // DOU condition; ... ENDDO;
    dou_loop: $ => seq(
      ci('dou'),
      $.expression,
      ';',
      repeat($.statement),
      ci('enddo'),
      ';'
    ),

    // DO; ... ENDDO;   or   DO i = 1 to 10; ... ENDDO;
    do_loop: $ => seq(
      ci('do'),
      optional($.expression),
      ';',
      repeat($.statement),
      ci('enddo'),
      ';'
    ),

    // FOR i = 1 to 10; ... ENDFOR;
    for_loop: $ => seq(
      ci('for'),
      optional($.expression),
      ';',
      repeat($.statement),
      ci('endfor'),
      ';'
    ),

    // MONITOR; ... ON-ERROR [expr]; ... ENDMON;
    monitor_statement: $ => seq(
      ci('monitor'),
      ';',
      repeat($.statement),
      repeat($.on_error_clause),
      ci('endmon'),
      ';'
    ),

    on_error_clause: $ => seq(
      ci('on-error'),
      optional($.expression),
      ';',
      repeat($.statement)
    ),

    // RETURN [expr];
    return_statement: $ => seq(
      ci('return'),
      optional($.expression),
      ';'
    ),

    // ------------------------------------------------------------------
    // Expressions
    // ------------------------------------------------------------------
    // NOTE: RPG reuses "=" for both equality and assignment; this grammar
    // treats "=" as a generic binary operator so constructs like:
    //   if a = b;
    // and
    //   x = 1;
    // are both parsed as binary expressions.

    expression: $ => $.logical_or_expression,

    logical_or_expression: $ => seq(
      $.logical_and_expression,
      repeat(seq(
        field('operator', choice(ci('or'), ci('*or'))),
        $.logical_and_expression
      ))
    ),

    logical_and_expression: $ => seq(
      $.equality_expression,
      repeat(seq(
        field('operator', choice(ci('and'), ci('*and'))),
        $.equality_expression
      ))
    ),

    equality_expression: $ => seq(
      $.relational_expression,
      repeat(seq(
        field('operator', choice('=', '<>', '!=', '==')),
        $.relational_expression
      ))
    ),

    relational_expression: $ => seq(
      $.additive_expression,
      repeat(seq(
        field('operator', choice('<', '<=', '>', '>=')),
        $.additive_expression
      ))
    ),

    additive_expression: $ => seq(
      $.multiplicative_expression,
      repeat(seq(
        field('operator', choice('+', '-')),
        $.multiplicative_expression
      ))
    ),

    multiplicative_expression: $ => seq(
      $.unary_expression,
      repeat(seq(
        field('operator', choice('*', '/', '%')),
        $.unary_expression
      ))
    ),

    unary_expression: $ => choice(
      seq(
        field('operator', choice('-', '+', ci('not'), ci('*not'))),
        $.unary_expression
      ),
      $.call_expression,
      $.primary_expression
    ),

    // function/procedure/builtin calls and array indexing:
    //   Proc(a : b);
    //   %trim(name);
    //   arr(i);
    call_expression: $ => seq(
      $.primary_expression,
      '(',
      optional(sep1($.expression, choice(',', ':'))),
      ')'
    ),

    primary_expression: $ => choice(
      $.qualified_identifier,
      $.simple_identifier,
      $.number_literal,
      $.string_literal,
      $.parenthesized_expression
    ),

    parenthesized_expression: $ => seq(
      '(',
      $.expression,
      ')'
    ),

    // ds.subfield.more
    qualified_identifier: $ => seq(
      $.simple_identifier,
      repeat1(seq('.', $.identifier))
    ),

    simple_identifier: $ => choice(
      $.identifier,
      $.special_identifier,
      $.builtin_function
    ),

    // ------------------------------------------------------------------
    // Lexical tokens
    // ------------------------------------------------------------------
    identifier: $ => /[A-Za-z_#@$][A-Za-z0-9_#@$]*/,

    // For things like *N, *INLR, *ON, *OFF, *NULL, etc.
    identifier_or_star: $ => choice(
      $.identifier,
      $.special_identifier
    ),

    special_identifier: $ => /\*[A-Za-z0-9_#@$]+/,

    // %trim, %scan, %len, %lookup, %subarr, etc.
    builtin_function: $ => /%[A-Za-z_][A-Za-z0-9_]*/,

    number_literal: $ => /\d+(\.\d+)?([eE][+-]?\d+)?/,

    // RPG strings use single quotes; double quotes are also allowed
    string_literal: $ => token(choice(
      /'([^']|'')*'/,
      /"([^"]|"")*"/
    )),

    comment: $ => token(choice(
      seq('//', /[^\n]*/),
      /\/\*([^*]|\*[^\/])*\*\//
    )),
  }
});
```

---

### How to use it

Quick setup steps (minimal):

1. Make a repo like `tree-sitter-rpg` with:

   * `grammar.js` (the file above)
   * a simple `package.json`:

   ```json
   {
     "name": "tree-sitter-rpg",
     "version": "0.1.0",
     "main": "index.js",
     "keywords": ["tree-sitter", "rpg", "ile rpg", "rpgle"],
     "license": "MIT",
     "dependencies": {
       "tree-sitter": "^0.22.0"
     }
   }
   ```

2. Run `npm install` then `npx tree-sitter generate` to build the parser.

3. Point your editor (Neovim, Emacs, VS Code extension, etc.) at the built language.

---

If you tell me:

* whether you care about **fixed‑format** (H/F/D/I/C/O/P)
* and whether this is for **syntax highlighting only** or more advanced tooling

…I can extend this grammar (in this same chat) to cover more of what you need (e.g. fixed‑form layout, embedded SQL, ON‑EXIT, BIF lists, etc.).

[1]: https://www.ibm.com/docs/en/i/7.4.0?topic=statements-fully-free-form "Fully free-form statements"
[2]: https://www.ibm.com/docs/en/i/7.4.0?topic=specifications-free-form-definition-statement&utm_source=chatgpt.com "Free-Form Definition Statement"
[3]: https://www.certlibrary.com/blog/rpg-iv-essentials-learn-ibms-business-programming-language/?utm_source=chatgpt.com "RPG IV Essentials: Learn IBM's Business Programming ..."
[4]: https://www.ibm.com/docs/en/i/7.4.0?topic=specifications-rpg-iv-specification-types "RPG IV Specification Types"

