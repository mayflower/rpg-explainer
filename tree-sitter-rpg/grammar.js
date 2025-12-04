// Tree-sitter grammar for IBM ILE RPG (fully free-form)
// Simplified version with minimal ambiguity

function escapeRegex(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// Case-insensitive keyword helper
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

module.exports = grammar({
  name: 'rpg',

  extras: $ => [
    /\s/,
    $.comment,
  ],

  word: $ => $.identifier,

  rules: {
    // Top-level: just a sequence of declarations and statements
    source_file: $ => repeat($._item),

    _item: $ => choice(
      $.procedure_definition,
      $.file_definition,
      $.data_structure_definition,
      $.procedure_prototype,
      $.constant_definition,
      $.variable_definition,
      $.ctl_opt,
      $.preprocessor_directive,
      $.if_statement,
      $.dow_statement,
      $.dou_statement,
      $.for_statement,
      $.select_statement,
      $.monitor_statement,
      $.return_statement,
      $.simple_statement
    ),

    // Control options: ctl-opt ... ;
    ctl_opt: $ => seq(
      ci('ctl-opt'),
      repeat($._token),
      ';'
    ),

    // Preprocessor: /COPY, /IF, etc.
    preprocessor_directive: $ => token(seq('/', /[A-Za-z]+/, /[^\n]*/)),

    // File definition: DCL-F name ... ;
    file_definition: $ => seq(
      ci('dcl-f'),
      field('name', $.identifier),
      repeat($._token),
      ';'
    ),

    // Variable definition: DCL-S name ... ;
    variable_definition: $ => seq(
      ci('dcl-s'),
      field('name', $._name),
      repeat($._token),
      ';'
    ),

    // Constant definition: DCL-C name ... ;
    constant_definition: $ => seq(
      ci('dcl-c'),
      field('name', $._name),
      repeat($._token),
      ';'
    ),

    // Data structure: DCL-DS name ... ; ... END-DS ;
    data_structure_definition: $ => seq(
      ci('dcl-ds'),
      field('name', $._name),
      repeat($._token),
      ';',
      repeat($.subfield_definition),
      ci('end-ds'),
      optional($._name),
      ';'
    ),

    subfield_definition: $ => seq(
      optional(ci('dcl-subf')),
      field('name', $._name),
      repeat($._token),
      ';'
    ),

    // Procedure prototype: DCL-PR name ... ; params ; END-PR ;
    procedure_prototype: $ => seq(
      ci('dcl-pr'),
      field('name', $._name),
      repeat($._token),
      ';',
      repeat($.parameter_definition),
      ci('end-pr'),
      optional($._name),
      ';'
    ),

    // Procedure interface: DCL-PI name ... ; params ; END-PI ;
    procedure_interface: $ => seq(
      ci('dcl-pi'),
      field('name', $._name),
      repeat($._token),
      ';',
      repeat($.parameter_definition),
      ci('end-pi'),
      optional($._name),
      ';'
    ),

    parameter_definition: $ => seq(
      optional(ci('dcl-parm')),
      field('name', $._name),
      repeat($._token),
      ';'
    ),

    // Procedure definition: DCL-PROC name ... ; body ; END-PROC ;
    procedure_definition: $ => seq(
      ci('dcl-proc'),
      field('name', $.identifier),
      repeat($._token),
      ';',
      repeat($._proc_item),
      ci('end-proc'),
      optional($.identifier),
      ';'
    ),

    _proc_item: $ => choice(
      $.procedure_interface,
      $.variable_definition,
      $.if_statement,
      $.dow_statement,
      $.dou_statement,
      $.for_statement,
      $.select_statement,
      $.monitor_statement,
      $.return_statement,
      $.simple_statement
    ),

    // Control flow statements
    if_statement: $ => seq(
      ci('if'),
      repeat($._token),
      ';',
      repeat($._proc_item),
      repeat($.elseif_clause),
      optional($.else_clause),
      ci('endif'),
      ';'
    ),

    elseif_clause: $ => seq(
      ci('elseif'),
      repeat($._token),
      ';',
      repeat($._proc_item)
    ),

    else_clause: $ => seq(
      ci('else'),
      ';',
      repeat($._proc_item)
    ),

    dow_statement: $ => seq(
      ci('dow'),
      repeat($._token),
      ';',
      repeat($._proc_item),
      ci('enddo'),
      ';'
    ),

    dou_statement: $ => seq(
      ci('dou'),
      repeat($._token),
      ';',
      repeat($._proc_item),
      ci('enddo'),
      ';'
    ),

    for_statement: $ => seq(
      ci('for'),
      repeat($._token),
      ';',
      repeat($._proc_item),
      ci('endfor'),
      ';'
    ),

    select_statement: $ => seq(
      ci('select'),
      optional(seq(repeat1($._token))),
      ';',
      repeat($.when_clause),
      optional($.other_clause),
      ci('endsl'),
      ';'
    ),

    when_clause: $ => seq(
      ci('when'),
      repeat($._token),
      ';',
      repeat($._proc_item)
    ),

    other_clause: $ => seq(
      ci('other'),
      ';',
      repeat($._proc_item)
    ),

    monitor_statement: $ => seq(
      ci('monitor'),
      ';',
      repeat($._proc_item),
      repeat($.on_error_clause),
      ci('endmon'),
      ';'
    ),

    on_error_clause: $ => seq(
      ci('on-error'),
      optional(seq(repeat1($._token))),
      ';',
      repeat($._proc_item)
    ),

    return_statement: $ => seq(
      ci('return'),
      optional(seq(repeat1($._token))),
      ';'
    ),

    // Simple statement (expression statement)
    simple_statement: $ => seq(
      repeat1($._token),
      ';'
    ),

    // Generic token - anything that's not a semicolon or structure keyword
    _token: $ => choice(
      $.identifier,
      $.special_identifier,
      $.builtin_function,
      $.number_literal,
      $.string_literal,
      $.operator,
      $.paren_group
    ),

    paren_group: $ => seq('(', repeat($._paren_item), ')'),

    _paren_item: $ => choice(
      $.identifier,
      $.special_identifier,
      $.builtin_function,
      $.number_literal,
      $.string_literal,
      $.operator,
      $.paren_group,
      ',',
      ':'
    ),

    operator: $ => token(choice(
      '=', '<>', '!=', '==',
      '<', '<=', '>', '>=',
      '+', '-', '*', '/', '%',
      '+=', '-=',
      '.'
    )),

    _name: $ => choice($.identifier, $.special_identifier),

    // Lexical tokens
    identifier: $ => /[A-Za-z_#@$][A-Za-z0-9_#@$]*/,
    special_identifier: $ => /\*[A-Za-z0-9_#@$]+/,
    builtin_function: $ => /%[A-Za-z_][A-Za-z0-9_]*/,
    number_literal: $ => /-?\d+(\.\d+)?([eE][+-]?\d+)?/,
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
