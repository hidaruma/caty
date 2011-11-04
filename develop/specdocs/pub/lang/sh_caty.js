/* -*- coding : utf-8 -*- */

if (! this.sh_languages) {
  this.sh_languages = {};
}
sh_languages['caty'] = [
/* 0 */
  [
    [
      /\/\//g,
      'sh_comment',
      7 // in_1L_comment
    ],
    [
      /\/\*\*/g,
      'sh_doccomment',
      8 // in_doc_comment
    ],
    [
      /\/\*/g,
      'sh_comment',
      9 // in_comment
    ],
    [
      /\b(?:module|type|command|deferred|null|boolean|string|binary|number|integer|undefined|any|void)\b/g,
      'sh_keyword',
      -1
    ],
    [
      /(\+\+|--|\)|\])(\s*)(\/=?(?![*\/]))/g,
      ['sh_symbol', 'sh_normal', 'sh_symbol'],
      -1
    ],
    [
      /(0x[A-Fa-f0-9]+|(?:[\d]*\.)?[\d]+(?:[eE][+-]?[\d]+)?)(\s*)(\/(?![*\/]))/g,
      ['sh_number', 'sh_normal', 'sh_symbol'],
      -1
    ],
    [
      /([A-Za-z$_][A-Za-z0-9$_]*\s*)(\/=?(?![*\/]))/g,
      ['sh_normal', 'sh_symbol'],
      -1
    ],
    [
      /\b[+-]?(?:(?:0x[A-Fa-f0-9]+)|(?:(?:[\d]*\.)?[\d]+(?:[eE][+-]?[\d]+)?))u?(?:(?:int(?:8|16|32|64))|L)?\b/g,
      'sh_number',
      -1
    ],
    [
      /"/g,
      'sh_string',
      10 // in_string
    ],
    [
      /~|!|@|%|\^|\*|\(|\)|-|\+|=|\[|\]|\\|:|;|,|\.|\/|\?|&|<|>|\|/g,
      'sh_symbol',
      -1
    ],
    [
      /\{|\}/g,
      'sh_cbracket',
      -1
    ],
/*
    [
      /\b(?:)\b/g,
      'sh_predef_var',
      -1
    ]
*/
  ],
/* 1 */ // in_xml
  [
    [
      /$/g,
      null,
      -2
    ],
    [
      /(?:<?)[A-Za-z0-9_\.\/\-_~]+@[A-Za-z0-9_\.\/\-_~]+(?:>?)|(?:<?)[A-Za-z0-9_]+:\/\/[A-Za-z0-9_\.\/\-_~]+(?:>?)/g,
      'sh_url',
      -1
    ],
    [
      /<\?xml/g,
      'sh_preproc',
      2, // in_xml_pi
      1
    ],
    [
      /<!DOCTYPE/g,
      'sh_preproc',
      4, // in_xml_decl
      1
    ],
    [
      /<!--/g,
      'sh_comment',
      5 // in_xml_comment
    ],
    [
      /<(?:\/)?[A-Za-z](?:[A-Za-z0-9_:.-]*)(?:\/)?>/g,
      'sh_keyword',
      -1
    ],
    [
      /<(?:\/)?[A-Za-z](?:[A-Za-z0-9_:.-]*)/g,
      'sh_keyword',
      6, // in_keyword
      1
    ],
    [
      /&(?:[A-Za-z0-9]+);/g,
      'sh_preproc',
      -1
    ],
    [
      /<(?:\/)?[A-Za-z][A-Za-z0-9]*(?:\/)?>/g,
      'sh_keyword',
      -1
    ],
    [
      /<(?:\/)?[A-Za-z][A-Za-z0-9]*/g,
      'sh_keyword',
      6, // in_keyword
      1
    ],
    [
      /@[A-Za-z]+/g,
      'sh_type',
      -1
    ],
    [
      /(?:TODO|FIXME|BUG)(?:[:]?)/g,
      'sh_todo',
      -1
    ]
  ],
/* 2 */ // in_xml_pi
  [
    [
      /\?>/g,
      'sh_preproc',
      -2
    ],
    [
      /([^=" \t>]+)([ \t]*)(=?)/g,
      ['sh_type', 'sh_normal', 'sh_symbol'],
      -1
    ],
    [
      /"/g,
      'sh_string',
      3 // in_string1
    ]
  ],
/* 3 */ // in_string1
  [
    [
      /\\(?:\\|")/g,
      null,
      -1
    ],
    [
      /"/g,
      'sh_string',
      -2
    ]
  ],
/* 4 */ // in_xml_decl
  [
    [
      />/g,
      'sh_preproc',
      -2
    ],
    [
      /([^=" \t>]+)([ \t]*)(=?)/g,
      ['sh_type', 'sh_normal', 'sh_symbol'],
      -1
    ],
    [
      /"/g,
      'sh_string',
      3 // in_string1
    ]
  ],
/* 5 */ // in_xml_comment
  [
    [
      /-->/g,
      'sh_comment',
      -2
    ],
    [
      /<!--/g,
      'sh_comment',
      5 // in_xml_comment
    ]
  ],
/* 6 */ // in_keyword
  [
    [
      /(?:\/)?>/g,
      'sh_keyword',
      -2
    ],
    [
      /([^=" \t>]+)([ \t]*)(=?)/g,
      ['sh_type', 'sh_normal', 'sh_symbol'],
      -1
    ],
    [
      /"/g,
      'sh_string',
      3 // in_string1
    ]
  ],
/* 7 */ // in_1L_comment
  [
    [
      /$/g,
      null,
      -2
    ]
  ],
/* 8 */ // in_doc_coment
  [
    [
      /\*\//g,
      'sh_doccomment',
      -2
    ],
    [
      /(?:<?)[A-Za-z0-9_\.\/\-_~]+@[A-Za-z0-9_\.\/\-_~]+(?:>?)|(?:<?)[A-Za-z0-9_]+:\/\/[A-Za-z0-9_\.\/\-_~]+(?:>?)/g,
      'sh_url',
      -1
    ],
    [
      /<\?xml/g,
      'sh_preproc',
      2, // in_xml_pi
      1
    ],
    [
      /<!DOCTYPE/g,
      'sh_preproc',
      4, // in_xml_decl
      1
    ],
    [
      /<!--/g,
      'sh_comment',
      5 // in_xml_comment
    ],
    [
      /<(?:\/)?[A-Za-z](?:[A-Za-z0-9_:.-]*)(?:\/)?>/g,
      'sh_keyword',
      -1
    ],
    [
      /<(?:\/)?[A-Za-z](?:[A-Za-z0-9_:.-]*)/g,
      'sh_keyword',
      6, // in_keyword
      1
    ],
    [
      /&(?:[A-Za-z0-9]+);/g,
      'sh_preproc',
      -1
    ],
    [
      /<(?:\/)?[A-Za-z][A-Za-z0-9]*(?:\/)?>/g,
      'sh_keyword',
      -1
    ],
    [
      /<(?:\/)?[A-Za-z][A-Za-z0-9]*/g,
      'sh_keyword',
      6, // in_keyword
      1
    ],
    [
      /@[A-Za-z]+/g,
      'sh_type',
      -1
    ],
    [
      /(?:TODO|FIXME|BUG)(?:[:]?)/g,
      'sh_todo',
      -1
    ]
  ],
/* 9 */ // in_comment
  [
    [
      /\*\//g,
      'sh_comment',
      -2
    ],
    [
      /(?:<?)[A-Za-z0-9_\.\/\-_~]+@[A-Za-z0-9_\.\/\-_~]+(?:>?)|(?:<?)[A-Za-z0-9_]+:\/\/[A-Za-z0-9_\.\/\-_~]+(?:>?)/g,
      'sh_url',
      -1
    ],
    [
      /(?:TODO|FIXME|BUG)(?:[:]?)/g,
      'sh_todo',
      -1
    ]
  ],
/* 10 */ // in_string
  [
    [
      /"/g,
      'sh_string',
      -2
    ],
    [
      /\\./g,
      'sh_specialchar',
      -1
    ]
  ]

];
