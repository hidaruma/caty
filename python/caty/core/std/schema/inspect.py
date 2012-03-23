#coding: utf-8
name = u'inspect'
schema = u"""
type typeExprText = string(remark="型表現のテキスト");
type exceptionName = string(remark="例外の名前");


/** コマンドプロファイル情報の簡易版 */
type ShortProfile = {
 /** コマンドの名前 */
 "name" : string,

 /** コマンドの型引数
  * コマンドが多相IOプロファイルを持つとき、束縛型変数（名前文字列）のリストを指定する。
  * IOプロファイルが具体的（単相）なときは空配列。
  */
 "typeVars" : [string*],

 /** 実装状況 */
 "implemented" : implemented?,

 /** オプションの型 */
 "opts" : typeExprText,

 /** 引数の型 
  * arg0は含まれないので、args[0]がargv[1]であることに注意
  */
 "args" : typeExprText,

 /** 入力の型 */
 "input" : typeExprText,

 /** 出力の型 */
 "output" : typeExprText,

 /** 例外の型 */
 "throws" : ([exceptionName*] | @only [exceptionName*])?,

 /** deprecatedか否か */
 "deprecated" : boolean,

 /** ファシリティの利用宣言 */
 //"facilityUsages": [FacilityUsage*]?,
 * : any?
};

/** 実装状況を示す値 
 */
type implemented = (
  /** 実装はない、宣言されているだけ */
  "none" |

  /** Python実装を持つ */
  "python" |

  /** CatyScript実装を持つ */
  "catyscript" |
);

/**
 * ファシリティの利用宣言
 */
type FacilityUsage = {
    "facilityName": string,
    "usageType": "reads" | "updates" | "uses",
};

/** モジュールに含まれるコマンドを列挙する
 * 引数に指定されたモジュールに固有なコマンドだけを列挙する。
 * 別名として存在するコマンドや、そのモジュールから可視な別モジュールのコマンドは列挙しない。
 * 
 * モジュール名はパッケージ修飾を許す。
 * またアプリケーション名で修飾してもよい。
 * 例：
 *  * mymod
 *  * pkg.mymod
 *  * otherapp:somepkg.yourmod
 *  * this:pkg.mymod
 */
command list-cmd 
 {
   /** 当面、shortオプションのデフォルトはtrue */
   @[default(true)]
   "short" : boolean?,
 }
 [string moduleName] :: void -> [ShortProfile*]
 throws ModuleNotFound
 refers python:caty.core.std.command.inspect.ListCommands;


/** モジュール情報 */
type Module = {

 /** モジュールの名前 
  * パッケージ修飾されている可能性がある。
  */
 "name" : string,

 /** モジュールの記述構文 */
 "syntax" : ("casm" | "cara"), // "camb" はとりあえず除いておく

 /** モジュールが置かれている場所 */
 "place" : ("schemata" | "actions")
};

/** アプリケーションに含まれるモジュールを列挙する
 * 引数に指定されたアプリケーションに固有なモジュールだけを列挙する。
 * そのアプリケーションから可視なモジュールでも別なアプリケーションに所属するモジュールは列挙しない。
 * アプリケーションとして caty が指定された場合は、
 * Catyコアに組み込みのモジュールを列挙する。
 *
 */
command list-mod
 [string appName] :: void -> [Module*]
 throws ApplicationNotFound
 refers python:caty.core.std.command.inspect.ListModules;


/**
 * 引数の型に対するレイフィケーションイメージを出力する。
 */
command reify-type [string typeName] :: void -> ReifiedTypeTerm | RTypeDef
    throws [ApplicationNotFound, ModuleNotFound, TypeNotFound]
    reads schema
    refers python:caty.core.std.command.inspect.ReifyType;

/*レイフィケーション関係*/

type ReifiedModule = @module {
    "name": string,
    "docstring": string,
    "type": "casm" | "cara",
    "member": {
        *: ReifiedTypeTerm | ReifiedKind | ReifiedCommand | ReifiedAction,
    },
};

type TypeAttribute = {
    "annotation": (@annotation [ReifiedAnnotation*])?,
    "options": object?,
    "docstring": string?
};

type ReifiedAnnotation = {
    "name": string,
    "value": any,
};

type ReifiedTypeTerm = @type (TypeAttribute ++ {
    "name": string(remark="型名"),
    "typeParams": [RTypeParam*] | null,
    "typeBody": RTypeDef,
});

type RTypeDef = (RObject 
                | RArray 
                | REnum
                | RBag
                | RScalar
                | RUnion
                | RIntersection
                | RUpdator
                | ROptional
                | RTag);

type RObject = @_object (
    TypeAttribute ++ {
        "items": {*: RTypeDef}, 
        "wildcard": RTypeDef,
        "pseudoTag": RPseudoTag?,
    });

type RPseudoTag = @_pseudoTag ([string, any] | [null, null]);
type RArray = @_array (TypeAttribute ++ {"items": [RTypeDef*]});
type RBag = @_bag (TypeAttribute ++ {"items": [RTypeDef*]});
type REnum = @_enum (TypeAttribute ++ {"enum": [(string|integer|number|boolean|null)*]});
type RUnion = @_union (TypeAttribute ++ {"left": RTypeDef, "right": RTypeDef});
type RIntersection = @_intersection (TypeAttribute ++ {"left": RTypeDef, "right": RTypeDef});
type RUpdator = @_updator (TypeAttribute ++ {"left": RTypeDef, "right": RTypeDef});
type RScalar = @_scalar (TypeAttribute ++ {
    "name": string(remark="参照している型名"),
    "typeArgs": [RTypeDef*],
    }
);
type RTypeParam = @_typeparam {
    "var_name": string,
    "kind": string | null,
    "default": string | null,
};

type RTag = @_tag (TypeAttribute ++ {
    "tag": string,
    "body": RTypeDef,
});
type ROptional = @_optional (TypeAttribute ++ {"body": RTypeDef});
type ReifiedAction = @action object;
type ReifiedKind = @kind object;

type ReifiedCommand = @command (RHostLangCommand | RScriptCommand | RStubCommand);

type CommandAttribute = {
    "name": string,
    "annotation": @annotation [ReifiedAnnotation*],
    "typeParams": [RTypeParam*]?,
    "docstring": string?,
    "profiles": [RProfile],
    "exception": [string*]?,
    "resrouce": [FacilityUsage*]?,
};

type RProfile = {
    "opts": RObject,
    "args": RArray,
    "input": RTypeDef,
    "output": RTypeDef,
};

type RHostLangCommand = @_hostLang (CommandAttribute ++ {
    "refers": string,
    "script": undefined,
});

type RStubCommand = @_stub (CommandAttribute ++ {
    "refers": undefined,
    "script": undefined,
});

type RScriptCommand = @_script (CommandAttribute ++ {
    "refers": undefined,
    "script": ReifiedScript,
});

type ReifiedScript = (RCommandCall 
                    | RScalarVal
                    | RListBuilder 
                    | RObjectBuilder
                    | RTypeDispatch
                    | RTypeCase
                    | RTypeCond
                    | RTagBuilder
                    | RUnaryTagBuilder
                    | RFunctor
                    | RFragment
                    | RJson
                    | RPipe
                    | RDiscard
                    | RVarStore
                    | RVarRef
                    | RArgRef);

type RCommandCall = @_call {
    "name": string,
    "opts": [ROptProxy],
    "args": [RArgProxy],
    "typeArgs": [string*],
    "pos": [integer, integer],
};

type ROptProxy = ROption | ROptionLoader | ROptionVarLoader | RGlobOption;

type ROption = @_opt {
    "key": string,
    "value": any,
    "optional": undefined,
};

type ROptionLoader = @_optLoader {
    "key": string,
    "value": undefined,
    "optional": boolean,
};

type ROptionVarLoader = @_optVarLoader {
    "key": string,
    "value": any,
    "optional": boolean,
};

type RGlobOption = @_glob {};

type RArgProxy = RArgument | RNamedArg | RIndexArg | RGlobArg;

type RArgument = @_arg {
    "value": any,
};

type RNamedArg = @_narg {
    "key": any,
    "optional": boolean,
};


type RIndexArg = @_iarg {
    "index": any,
    "optional": boolean,
};


type RGlobArg = @_garg {
};

type RScalarVal = @_scalar string|binary|integer|number|null;

type RListBuilder = @_list [ReifiedScript*];

type RObjectBuilder = @_object {*: ReifiedScript};

type RTypeDispatch = @_when {"opts": ROptProxy, "cases": [(RTagBuilder|RUntag)*]};

type RTagBuilder = @_tag {"tag": string, "value": ReifiedScript};

type RUntag = @_untag  {"tag": string, "value": ReifiedScript};

type RUnaryTagBuilder = @_unaryTag {"tag": string};

type RTypeCase = @_case {
    "path": string?,
    "via": ReifiedScript?,
    "cases": [RCaseNode*],
};

type RTypeCond = @_cond {
    "path": string?,
    "cases": [RCaseNode*],
};

type RCaseNode = {
    "type": RTypeDef,
    "body": ReifiedScript
};

type RFunctor = REach | RTake | RTime | RStart;

type REach = @_each FunctorBody;
type RTake = @_take FunctorBody;
type RTime = @_time FunctorBody;
type RStart = @_start FunctorBody;

type FunctorBody = {"opts": ROptProxy, "body": ReifiedScript};

type RFragment = @_fragment {
    "name": string,
    "body": ReifiedScript,
};

type RJson = @_jsonPath {
    "path": string,
    "pos": [integer, integer],
};

type RPipe = @_pipe [ReifiedScript, ReifiedScript];
type RDiscard = @_discard [ReifiedScript, ReifiedScript];
type RVarStore = @_store {"name": string};
type RVarRef = @_varref {"name": string, "optional": boolean};
type RArgRef = @_argref {"name": string, "optional": boolean};

"""
