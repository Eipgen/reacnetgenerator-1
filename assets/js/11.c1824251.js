(window.webpackJsonp=window.webpackJsonp||[]).push([[11],{372:function(a,e,t){"use strict";t.r(e);var n=t(45),s=Object(n.a)({},(function(){var a=this,e=a.$createElement,t=a._self._c||e;return t("ContentSlotsDistributor",{attrs:{"slot-key":a.$parent.slotKey}},[t("h1",{attrs:{id:"guide"}},[t("a",{staticClass:"header-anchor",attrs:{href:"#guide"}},[a._v("#")]),a._v(" Guide")]),a._v(" "),t("p",[a._v("ReacNetGenerator is an automatic reaction network generator for reactive molecular dynamics simulation. This page provides a easy way to start it.")]),a._v(" "),t("h2",{attrs:{id:"installation"}},[t("a",{staticClass:"header-anchor",attrs:{href:"#installation"}},[a._v("#")]),a._v(" Installation")]),a._v(" "),t("p",[a._v("You can easily use "),t("code",[a._v("pip")]),a._v(" to install ReacNetGenerator:")]),a._v(" "),t("div",{staticClass:"language-bash extra-class"},[t("pre",{pre:!0,attrs:{class:"language-bash"}},[t("code",[a._v("pip "),t("span",{pre:!0,attrs:{class:"token function"}},[a._v("install")]),a._v(" reacnetgenerator\n")])])]),t("p",[a._v("You can also "),t("a",{attrs:{href:"https://conda.io/projects/continuumio-conda/en/latest/user-guide/install/index.html",target:"_blank",rel:"noopener noreferrer"}},[a._v("install Anaconda or Miniconda"),t("OutboundLink")],1),a._v(" to obtain conda, and install ReacNetGenerator easily with conda:")]),a._v(" "),t("div",{staticClass:"language-bash extra-class"},[t("pre",{pre:!0,attrs:{class:"language-bash"}},[t("code",[a._v("conda "),t("span",{pre:!0,attrs:{class:"token function"}},[a._v("install")]),a._v(" reacnetgenerator -c conda-forge\n")])])]),t("p",[a._v("See "),t("RouterLink",{attrs:{to:"/guide/build.html"}},[a._v("the build guide")]),a._v(" if you want to build ReacNetGenerator by yourself.")],1),a._v(" "),t("h2",{attrs:{id:"usage"}},[t("a",{staticClass:"header-anchor",attrs:{href:"#usage"}},[a._v("#")]),a._v(" Usage")]),a._v(" "),t("h3",{attrs:{id:"command-line"}},[t("a",{staticClass:"header-anchor",attrs:{href:"#command-line"}},[a._v("#")]),a._v(" Command line")]),a._v(" "),t("p",[a._v("ReacNetGenerator can process any kind of trajectory files containing atomic coordinates, e.g. a LAMMPS dump file prepared by running “dump 1 all custom 100 dump.reaxc id type x y z” in LAMMPS:")]),a._v(" "),t("div",{staticClass:"language-bash extra-class"},[t("pre",{pre:!0,attrs:{class:"language-bash"}},[t("code",[a._v("reacnetgenerator --dump -i dump.reaxc -a C H O\n")])])]),t("p",[a._v("where C, H, and O are atomic names in the input file. "),t("a",{attrs:{href:"/report.html?jdata=https%3A%2F%2Fgist.githubusercontent.com%2Fnjzjz%2Fe9a4b42ceb7d2c3c7ada189f38708bf3%2Fraw%2F83d01b9ab1780b0ad2d1e7f934e61fa113cb0f9f%2Fmethane.json",target:"_blank"}},[a._v("Analysis report")]),a._v(" will be generated automatically.")]),a._v(" "),t("p",[a._v("Also, ReacNetGenerator can process files containing bond information, e.g. LAMMPS bond file:")]),a._v(" "),t("div",{staticClass:"language-bash extra-class"},[t("pre",{pre:!0,attrs:{class:"language-bash"}},[t("code",[a._v("reacnetgenerator -i bonds.reaxc -a C H O\n")])])]),t("p",[a._v("You can running the following script for help:")]),a._v(" "),t("div",{staticClass:"language-bash extra-class"},[t("pre",{pre:!0,attrs:{class:"language-bash"}},[t("code",[a._v("reacnetgenerator -h\n")])])]),t("h3",{attrs:{id:"gui-version"}},[t("a",{staticClass:"header-anchor",attrs:{href:"#gui-version"}},[a._v("#")]),a._v(" GUI version")]),a._v(" "),t("p",[a._v("You can open a GUI version for ReacNetGenerator by typing:")]),a._v(" "),t("div",{staticClass:"language-bash extra-class"},[t("pre",{pre:!0,attrs:{class:"language-bash"}},[t("code",[a._v("reacnetgeneratorgui\n")])])])])}),[],!1,null,null,null);e.default=s.exports}}]);