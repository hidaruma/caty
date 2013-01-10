/* -*- coding: utf-8 -*-
 * fire.js 
 */

var FIRE_COLOR = "orangered";

var STATE = 1;
var ACTION = 2;
var PORT = 3;

var _node = {
    "node19": {
	type : STATE,
	start : true,
	name : "enter",
	targets : ["node2"]
    },
    "node5":{
	type : STATE,
	start : false,
	name : "login",
	targets :["node4", "node14", "node12"]
    },
    "node9":{
	type : STATE,
	start : false,
	name : "login-failed",
	targets : ["node4", "node14", "node12"]
    },

    "node2": {
	type: ACTION,
	start : false,
	name : "Login.get",
	targets : ["node5"]
    },
    "node4": {
	type: ACTION,
	start : false,
	name:"DoLogin.do-login",
	targets : ["node9", "node7"]
    },

    "node14" : {
	type: PORT,
	start : false,
	name:"new-user",
	targets : []
    },
    "node12" : {
	type: PORT,
	start : false,
	name:"dyn-cancel",
	targets : []
    },
    "node7":{
	type: PORT,
	start : false,
	name:"dyn-success",
	targets : []
    }
};

var fire = {};

fire.rand = function (n) {
    return Math.floor( Math.random() * n );
};

fire.init = function () {
    for (var elmId in _node) {
	var s = fire.findShape(elmId);
	_node[elmId].orig = s.getAttribute("fill");
    }
};

fire.chain = function (startNodeId) {
    var nodeId = startNodeId;
    while (true) {
	fire.burn(nodeId);
	var node = _node[nodeId];
	var targets = node.targets;
	var n = targets.length;
	if (n == 0) break; // 行き先がないとき
	nodeId = targets[fire.rand(n)];
    }
};

fire.findShape = function (elmId) {
    var g = document.getElementById(elmId);
    var type = _node[elmId].type;
    var shape = null;
    if (type == STATE) {
	shape = "polygon";
    } else {
	shape = "ellipse";
    }
    return g.getElementsByTagName(shape)[0];
};

fire.burn = function (elmId) {
    var s = fire.findShape(elmId);
    s.setAttribute("fill", FIRE_COLOR);
};

fire.clear = function (elmId){
    var s = fire.findShape(elmId);
    s.setAttribute("fill", _node[elmId].orig); 
};

fire.clearAll = function () {
    for (var elmId in _node) {
	fire.clear(elmId);
    }
};
