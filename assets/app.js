(()=>{var d0=Object.defineProperty;var p0=(s,t,e)=>t in s?d0(s,t,{enumerable:!0,configurable:!0,writable:!0,value:e}):s[t]=e;var Gt=(s,t,e)=>p0(s,typeof t!="symbol"?t+"":t,e);function Vi(s){if(s===void 0)throw new ReferenceError("this hasn't been initialised - super() hasn't been called");return s}function _p(s,t){s.prototype=Object.create(t.prototype),s.prototype.constructor=s,s.__proto__=t}var Fn={autoSleep:120,force3D:"auto",nullTargetWarn:1,units:{lineHeight:""}},Ko={duration:.5,overwrite:!1,delay:0},wh,an,Ne,li=1e8,Ee=1/li,gh=Math.PI*2,m0=gh/4,g0=0,vp=Math.sqrt,_0=Math.cos,v0=Math.sin,Ke=function(t){return typeof t=="string"},He=function(t){return typeof t=="function"},Gi=function(t){return typeof t=="number"},cl=function(t){return typeof t>"u"},Li=function(t){return typeof t=="object"},On=function(t){return t!==!1},Th=function(){return typeof window<"u"},Qa=function(t){return He(t)||Ke(t)},xp=typeof ArrayBuffer=="function"&&ArrayBuffer.isView||function(){},dn=Array.isArray,x0=/random\([^)]+\)/g,y0=/,\s*/g,cp=/(?:-?\.?\d|\.)+/gi,Eh=/[-+=.]*\d+[.e\-+]*\d*[e\-+]*\d*/g,qs=/[-+=.]*\d+[.e-]*\d*[a-z%]*/g,ch=/[-+=.]*\d+\.?\d*(?:e-|e\+)?\d*/gi,Ah=/[+-]=-?[.\d]+/,M0=/[^,'"\[\]\s]+/gi,S0=/^[+\-=e\s\d]*\d+[.\d]*([a-z]*|%)\s*$/i,ke,Pi,_h,Ch,Xn={},nl={},yp,Mp=function(t){return(nl=Nr(t,Xn))&&pn},hl=function(t,e){return console.warn("Invalid property",t,"set to",e,"Missing plugin? gsap.registerPlugin()")},Qo=function(t,e){return!e&&console.warn(t)},Sp=function(t,e){return t&&(Xn[t]=e)&&nl&&(nl[t]=e)||Xn},jo=function(){return 0},b0={suppressEvents:!0,isStart:!0,kill:!1},ja={suppressEvents:!0,kill:!1},w0={suppressEvents:!0},Rh={},ms=[],vh={},bp,Un={},hh={},hp=30,tl=[],Ph="",Ih=function(t){var e=t[0],n,i;if(Li(e)||He(e)||(t=[t]),!(n=(e._gsap||{}).harness)){for(i=tl.length;i--&&!tl[i].targetTest(e););n=tl[i]}for(i=t.length;i--;)t[i]&&(t[i]._gsap||(t[i]._gsap=new Nh(t[i],n)))||t.splice(i,1);return t},gs=function(t){return t._gsap||Ih(ci(t))[0]._gsap},Lh=function(t,e,n){return(n=t[e])&&He(n)?t[e]():cl(n)&&t.getAttribute&&t.getAttribute(e)||n},Tn=function(t,e){return(t=t.split(",")).forEach(e)||t},Ge=function(t){return Math.round(t*1e5)/1e5||0},Be=function(t){return Math.round(t*1e7)/1e7||0},Zs=function(t,e){var n=e.charAt(0),i=parseFloat(e.substr(2));return t=parseFloat(t),n==="+"?t+i:n==="-"?t-i:n==="*"?t*i:t/i},T0=function(t,e){for(var n=e.length,i=0;t.indexOf(e[i])<0&&++i<n;);return i<n},il=function(){var t=ms.length,e=ms.slice(0),n,i;for(vh={},ms.length=0,n=0;n<t;n++)i=e[n],i&&i._lazy&&(i.render(i._lazy[0],i._lazy[1],!0)._lazy=0)},Dh=function(t){return!!(t._initted||t._startAt||t.add)},wp=function(t,e,n,i){ms.length&&!an&&il(),t.render(e,n,i||!!(an&&e<0&&Dh(t))),ms.length&&!an&&il()},Tp=function(t){var e=parseFloat(t);return(e||e===0)&&(t+"").match(M0).length<2?e:Ke(t)?t.trim():t},Ep=function(t){return t},Yn=function(t,e){for(var n in e)n in t||(t[n]=e[n]);return t},E0=function(t){return function(e,n){for(var i in n)i in e||i==="duration"&&t||i==="ease"||(e[i]=n[i])}},Nr=function(t,e){for(var n in e)t[n]=e[n];return t},up=function s(t,e){for(var n in e)n!=="__proto__"&&n!=="constructor"&&n!=="prototype"&&(t[n]=Li(e[n])?s(t[n]||(t[n]={}),e[n]):e[n]);return t},sl=function(t,e){var n={},i;for(i in t)i in e||(n[i]=t[i]);return n},Zo=function(t){var e=t.parent||ke,n=t.keyframes?E0(dn(t.keyframes)):Yn;if(On(t.inherit))for(;e;)n(t,e.vars.defaults),e=e.parent||e._dp;return t},A0=function(t,e){for(var n=t.length,i=n===e.length;i&&n--&&t[n]===e[n];);return n<0},Ap=function(t,e,n,i,r){n===void 0&&(n="_first"),i===void 0&&(i="_last");var o=t[i],a;if(r)for(a=e[r];o&&o[r]>a;)o=o._prev;return o?(e._next=o._next,o._next=e):(e._next=t[n],t[n]=e),e._next?e._next._prev=e:t[i]=e,e._prev=o,e.parent=e._dp=t,e},ul=function(t,e,n,i){n===void 0&&(n="_first"),i===void 0&&(i="_last");var r=e._prev,o=e._next;r?r._next=o:t[n]===e&&(t[n]=o),o?o._prev=r:t[i]===e&&(t[i]=r),e._next=e._prev=e.parent=null},_s=function(t,e){t.parent&&(!e||t.parent.autoRemoveChildren)&&t.parent.remove&&t.parent.remove(t),t._act=0},Ws=function(t,e){if(t&&(!e||e._end>t._dur||e._start<0))for(var n=t;n;)n._dirty=1,n=n.parent;return t},C0=function(t){for(var e=t.parent;e&&e.parent;)e._dirty=1,e.totalDuration(),e=e.parent;return t},xh=function(t,e,n,i){return t._startAt&&(an?t._startAt.revert(ja):t.vars.immediateRender&&!t.vars.autoRevert||t._startAt.render(e,!0,i))},R0=function s(t){return!t||t._ts&&s(t.parent)},fp=function(t){return t._repeat?Or(t._tTime,t=t.duration()+t._rDelay)*t:0},Or=function(t,e){var n=Math.floor(t=Be(t/e));return t&&n===t?n-1:n},rl=function(t,e){return(t-e._start)*e._ts+(e._ts>=0?0:e._dirty?e.totalDuration():e._tDur)},fl=function(t){return t._end=Be(t._start+(t._tDur/Math.abs(t._ts||t._rts||Ee)||0))},dl=function(t,e){var n=t._dp;return n&&n.smoothChildTiming&&t._ts&&(t._start=Be(n._time-(t._ts>0?e/t._ts:((t._dirty?t.totalDuration():t._tDur)-e)/-t._ts)),fl(t),n._dirty||Ws(n,t)),t},Cp=function(t,e){var n;if((e._time||!e._dur&&e._initted||e._start<t._time&&(e._dur||!e.add))&&(n=rl(t.rawTime(),e),(!e._dur||ia(0,e.totalDuration(),n)-e._tTime>Ee)&&e.render(n,!0)),Ws(t,e)._dp&&t._initted&&t._time>=t._dur&&t._ts){if(t._dur<t.duration())for(n=t;n._dp;)n.rawTime()>=0&&n.totalTime(n._tTime),n=n._dp;t._zTime=-Ee}},Ii=function(t,e,n,i){return e.parent&&_s(e),e._start=Be((Gi(n)?n:!n&&ol(e)&&(!t._last||t._last._start>=t._time)?t._last?t._last._start:t._time:n||t!==ke?ai(t,n,e):t._time)+e._delay),e._end=Be(e._start+(e.totalDuration()/Math.abs(e.timeScale())||0)),Ap(t,e,"_first","_last",t._sort?"_start":0),ol(e)||(t._recent=e),i||Cp(t,e),t._ts<0&&dl(t,t._tTime),t},Rp=function(t,e){return(Xn.ScrollTrigger||hl("scrollTrigger",e))&&Xn.ScrollTrigger.create(e,t)},Pp=function(t,e,n,i,r){if(Bh(t,e,r),!t._initted)return 1;if(!n&&t._pt&&!an&&(t._dur&&t.vars.lazy!==!1||!t._dur&&t.vars.lazy)&&bp!==Nn.frame)return ms.push(t),t._lazy=[r,i],1},P0=function s(t){var e=t.parent;return e&&e._ts&&e._initted&&!e._lock&&(e.rawTime()<0||s(e))},ol=function(t){var e=t.data;return e==="isFromStart"||e==="isStart"},I0=function(t,e,n,i){var r=t.ratio,o=e<0||!e&&(!t._start&&P0(t)&&!(!t._initted&&ol(t))||(t._ts<0||t._dp._ts<0)&&!ol(t))?0:1,a=t._rDelay,l=0,c,h,u;if(a&&t._repeat&&(l=ia(0,t._tDur,e),h=Or(l,a),t._yoyo&&h&1&&(o=1-o),h!==Or(t._tTime,a)&&(r=1-o,t.vars.repeatRefresh&&t._initted&&t.invalidate())),o!==r||an||i||t._zTime===Ee||!e&&t._zTime){if(!t._initted&&Pp(t,e,i,n,l))return;for(u=t._zTime,t._zTime=e||(n?Ee:0),n||(n=e&&!u),t.ratio=o,t._from&&(o=1-o),t._time=0,t._tTime=l,c=t._pt;c;)c.r(o,c.d),c=c._next;e<0&&xh(t,e,n,!0),t._onUpdate&&!n&&Wn(t,"onUpdate"),l&&t._repeat&&!n&&t.parent&&Wn(t,"onRepeat"),(e>=t._tDur||e<0)&&t.ratio===o&&(o&&_s(t,1),!n&&!an&&(Wn(t,o?"onComplete":"onReverseComplete",!0),t._prom&&t._prom()))}else t._zTime||(t._zTime=e)},L0=function(t,e,n){var i;if(n>e)for(i=t._first;i&&i._start<=n;){if(i.data==="isPause"&&i._start>e)return i;i=i._next}else for(i=t._last;i&&i._start>=n;){if(i.data==="isPause"&&i._start<e)return i;i=i._prev}},Fr=function(t,e,n,i){var r=t._repeat,o=Be(e)||0,a=t._tTime/t._tDur;return a&&!i&&(t._time*=o/t._dur),t._dur=o,t._tDur=r?r<0?1e10:Be(o*(r+1)+t._rDelay*r):o,a>0&&!i&&dl(t,t._tTime=t._tDur*a),t.parent&&fl(t),n||Ws(t.parent,t),t},dp=function(t){return t instanceof fn?Ws(t):Fr(t,t._dur)},D0={_start:0,endTime:jo,totalDuration:jo},ai=function s(t,e,n){var i=t.labels,r=t._recent||D0,o=t.duration()>=li?r.endTime(!1):t._dur,a,l,c;return Ke(e)&&(isNaN(e)||e in i)?(l=e.charAt(0),c=e.substr(-1)==="%",a=e.indexOf("="),l==="<"||l===">"?(a>=0&&(e=e.replace(/=/,"")),(l==="<"?r._start:r.endTime(r._repeat>=0))+(parseFloat(e.substr(1))||0)*(c?(a<0?r:n).totalDuration()/100:1)):a<0?(e in i||(i[e]=o),i[e]):(l=parseFloat(e.charAt(a-1)+e.substr(a+1)),c&&n&&(l=l/100*(dn(n)?n[0]:n).totalDuration()),a>1?s(t,e.substr(0,a-1),n)+l:o+l)):e==null?o:+e},$o=function(t,e,n){var i=Gi(e[1]),r=(i?2:1)+(t<2?0:1),o=e[r],a,l;if(i&&(o.duration=e[1]),o.parent=n,t){for(a=o,l=n;l&&!("immediateRender"in a);)a=l.vars.defaults||{},l=On(l.vars.inherit)&&l.parent;o.immediateRender=On(a.immediateRender),t<2?o.runBackwards=1:o.startAt=e[r-1]}return new Xe(e[0],o,e[r+1])},vs=function(t,e){return t||t===0?e(t):e},ia=function(t,e,n){return n<t?t:n>e?e:n},ln=function(t,e){return!Ke(t)||!(e=S0.exec(t))?"":e[1]},U0=function(t,e,n){return vs(n,function(i){return ia(t,e,i)})},yh=[].slice,Ip=function(t,e){return t&&Li(t)&&"length"in t&&(!e&&!t.length||t.length-1 in t&&Li(t[0]))&&!t.nodeType&&t!==Pi},N0=function(t,e,n){return n===void 0&&(n=[]),t.forEach(function(i){var r;return Ke(i)&&!e||Ip(i,1)?(r=n).push.apply(r,ci(i)):n.push(i)})||n},ci=function(t,e,n){return Ne&&!e&&Ne.selector?Ne.selector(t):Ke(t)&&!n&&(_h||!Br())?yh.call((e||Ch).querySelectorAll(t),0):dn(t)?N0(t,n):Ip(t)?yh.call(t,0):t?[t]:[]},Mh=function(t){return t=ci(t)[0]||Qo("Invalid scope")||{},function(e){var n=t.current||t.nativeElement||t;return ci(e,n.querySelectorAll?n:n===t?Qo("Invalid scope")||Ch.createElement("div"):t)}},Lp=function(t){return t.sort(function(){return .5-Math.random()})},Dp=function(t){if(He(t))return t;var e=Li(t)?t:{each:t},n=Xs(e.ease),i=e.from||0,r=parseFloat(e.base)||0,o={},a=i>0&&i<1,l=isNaN(i)||a,c=e.axis,h=i,u=i;return Ke(i)?h=u={center:.5,edges:.5,end:1}[i]||0:!a&&l&&(h=i[0],u=i[1]),function(f,d,g){var _=(g||e).length,m=o[_],p,S,y,v,E,A,T,R,M;if(!m){if(M=e.grid==="auto"?0:(e.grid||[1,li])[1],!M){for(T=-li;T<(T=g[M++].getBoundingClientRect().left)&&M<_;);M<_&&M--}for(m=o[_]=[],p=l?Math.min(M,_)*h-.5:i%M,S=M===li?0:l?_*u/M-.5:i/M|0,T=0,R=li,A=0;A<_;A++)y=A%M-p,v=S-(A/M|0),m[A]=E=c?Math.abs(c==="y"?v:y):vp(y*y+v*v),E>T&&(T=E),E<R&&(R=E);i==="random"&&Lp(m),m.max=T-R,m.min=R,m.v=_=(parseFloat(e.amount)||parseFloat(e.each)*(M>_?_-1:c?c==="y"?_/M:M:Math.max(M,_/M))||0)*(i==="edges"?-1:1),m.b=_<0?r-_:r,m.u=ln(e.amount||e.each)||0,n=n&&_<0?Z0(n):n}return _=(m[f]-m.min)/m.max||0,Be(m.b+(n?n(_):_)*m.v)+m.u}},Sh=function(t){var e=Math.pow(10,((t+"").split(".")[1]||"").length);return function(n){var i=Be(Math.round(parseFloat(n)/t)*t*e);return(i-i%1)/e+(Gi(n)?0:ln(n))}},Up=function(t,e){var n=dn(t),i,r;return!n&&Li(t)&&(i=n=t.radius||li,t.values?(t=ci(t.values),(r=!Gi(t[0]))&&(i*=i)):t=Sh(t.increment)),vs(e,n?He(t)?function(o){return r=t(o),Math.abs(r-o)<=i?r:o}:function(o){for(var a=parseFloat(r?o.x:o),l=parseFloat(r?o.y:0),c=li,h=0,u=t.length,f,d;u--;)r?(f=t[u].x-a,d=t[u].y-l,f=f*f+d*d):f=Math.abs(t[u]-a),f<c&&(c=f,h=u);return h=!i||c<=i?t[h]:o,r||h===o||Gi(o)?h:h+ln(o)}:Sh(t))},Np=function(t,e,n,i){return vs(dn(t)?!e:n===!0?!!(n=0):!i,function(){return dn(t)?t[~~(Math.random()*t.length)]:(n=n||1e-5)&&(i=n<1?Math.pow(10,(n+"").length-2):1)&&Math.floor(Math.round((t-n/2+Math.random()*(e-t+n*.99))/n)*n*i)/i})},O0=function(){for(var t=arguments.length,e=new Array(t),n=0;n<t;n++)e[n]=arguments[n];return function(i){return e.reduce(function(r,o){return o(r)},i)}},F0=function(t,e){return function(n){return t(parseFloat(n))+(e||ln(n))}},B0=function(t,e,n){return Fp(t,e,0,1,n)},Op=function(t,e,n){return vs(n,function(i){return t[~~e(i)]})},k0=function s(t,e,n){var i=e-t;return dn(t)?Op(t,s(0,t.length),e):vs(n,function(r){return(i+(r-t)%i)%i+t})},z0=function s(t,e,n){var i=e-t,r=i*2;return dn(t)?Op(t,s(0,t.length-1),e):vs(n,function(o){return o=(r+(o-t)%r)%r||0,t+(o>i?r-o:o)})},kr=function(t){return t.replace(x0,function(e){var n=e.indexOf("[")+1,i=e.substring(n||7,n?e.indexOf("]"):e.length-1).split(y0);return Np(n?i:+i[0],n?0:+i[1],+i[2]||1e-5)})},Fp=function(t,e,n,i,r){var o=e-t,a=i-n;return vs(r,function(l){return n+((l-t)/o*a||0)})},V0=function s(t,e,n,i){var r=isNaN(t+e)?0:function(d){return(1-d)*t+d*e};if(!r){var o=Ke(t),a={},l,c,h,u,f;if(n===!0&&(i=1)&&(n=null),o)t={p:t},e={p:e};else if(dn(t)&&!dn(e)){for(h=[],u=t.length,f=u-2,c=1;c<u;c++)h.push(s(t[c-1],t[c]));u--,r=function(g){g*=u;var _=Math.min(f,~~g);return h[_](g-_)},n=e}else i||(t=Nr(dn(t)?[]:{},t));if(!h){for(l in e)Oh.call(a,t,l,"get",e[l]);r=function(g){return Vh(g,a)||(o?t.p:t)}}}return vs(n,r)},pp=function(t,e,n){var i=t.labels,r=li,o,a,l;for(o in i)a=i[o]-e,a<0==!!n&&a&&r>(a=Math.abs(a))&&(l=o,r=a);return l},Wn=function(t,e,n){var i=t.vars,r=i[e],o=Ne,a=t._ctx,l,c,h;if(r)return l=i[e+"Params"],c=i.callbackScope||t,n&&ms.length&&il(),a&&(Ne=a),h=l?r.apply(c,l):r.call(c),Ne=o,h},Yo=function(t){return _s(t),t.scrollTrigger&&t.scrollTrigger.kill(!!an),t.progress()<1&&Wn(t,"onInterrupt"),t},Ur,Bp=[],kp=function(t){if(t)if(t=!t.name&&t.default||t,Th()||t.headless){var e=t.name,n=He(t),i=e&&!n&&t.init?function(){this._props=[]}:t,r={init:jo,render:Vh,add:Oh,kill:sv,modifier:iv,rawVars:0},o={targetTest:0,get:0,getSetter:pl,aliases:{},register:0};if(Br(),t!==i){if(Un[e])return;Yn(i,Yn(sl(t,r),o)),Nr(i.prototype,Nr(r,sl(t,o))),Un[i.prop=e]=i,t.targetTest&&(tl.push(i),Rh[e]=1),e=(e==="css"?"CSS":e.charAt(0).toUpperCase()+e.substr(1))+"Plugin"}Sp(e,i),t.register&&t.register(pn,i,En)}else Bp.push(t)},Pe=255,qo={aqua:[0,Pe,Pe],lime:[0,Pe,0],silver:[192,192,192],black:[0,0,0],maroon:[128,0,0],teal:[0,128,128],blue:[0,0,Pe],navy:[0,0,128],white:[Pe,Pe,Pe],olive:[128,128,0],yellow:[Pe,Pe,0],orange:[Pe,165,0],gray:[128,128,128],purple:[128,0,128],green:[0,128,0],red:[Pe,0,0],pink:[Pe,192,203],cyan:[0,Pe,Pe],transparent:[Pe,Pe,Pe,0]},uh=function(t,e,n){return t+=t<0?1:t>1?-1:0,(t*6<1?e+(n-e)*t*6:t<.5?n:t*3<2?e+(n-e)*(2/3-t)*6:e)*Pe+.5|0},zp=function(t,e,n){var i=t?Gi(t)?[t>>16,t>>8&Pe,t&Pe]:0:qo.black,r,o,a,l,c,h,u,f,d,g;if(!i){if(t.substr(-1)===","&&(t=t.substr(0,t.length-1)),qo[t])i=qo[t];else if(t.charAt(0)==="#"){if(t.length<6&&(r=t.charAt(1),o=t.charAt(2),a=t.charAt(3),t="#"+r+r+o+o+a+a+(t.length===5?t.charAt(4)+t.charAt(4):"")),t.length===9)return i=parseInt(t.substr(1,6),16),[i>>16,i>>8&Pe,i&Pe,parseInt(t.substr(7),16)/255];t=parseInt(t.substr(1),16),i=[t>>16,t>>8&Pe,t&Pe]}else if(t.substr(0,3)==="hsl"){if(i=g=t.match(cp),!e)l=+i[0]%360/360,c=+i[1]/100,h=+i[2]/100,o=h<=.5?h*(c+1):h+c-h*c,r=h*2-o,i.length>3&&(i[3]*=1),i[0]=uh(l+1/3,r,o),i[1]=uh(l,r,o),i[2]=uh(l-1/3,r,o);else if(~t.indexOf("="))return i=t.match(Eh),n&&i.length<4&&(i[3]=1),i}else i=t.match(cp)||qo.transparent;i=i.map(Number)}return e&&!g&&(r=i[0]/Pe,o=i[1]/Pe,a=i[2]/Pe,u=Math.max(r,o,a),f=Math.min(r,o,a),h=(u+f)/2,u===f?l=c=0:(d=u-f,c=h>.5?d/(2-u-f):d/(u+f),l=u===r?(o-a)/d+(o<a?6:0):u===o?(a-r)/d+2:(r-o)/d+4,l*=60),i[0]=~~(l+.5),i[1]=~~(c*100+.5),i[2]=~~(h*100+.5)),n&&i.length<4&&(i[3]=1),i},Vp=function(t){var e=[],n=[],i=-1;return t.split(Hi).forEach(function(r){var o=r.match(qs)||[];e.push.apply(e,o),n.push(i+=o.length+1)}),e.c=n,e},mp=function(t,e,n){var i="",r=(t+i).match(Hi),o=e?"hsla(":"rgba(",a=0,l,c,h,u;if(!r)return t;if(r=r.map(function(f){return(f=zp(f,e,1))&&o+(e?f[0]+","+f[1]+"%,"+f[2]+"%,"+f[3]:f.join(","))+")"}),n&&(h=Vp(t),l=n.c,l.join(i)!==h.c.join(i)))for(c=t.replace(Hi,"1").split(qs),u=c.length-1;a<u;a++)i+=c[a]+(~l.indexOf(a)?r.shift()||o+"0,0,0,0)":(h.length?h:r.length?r:n).shift());if(!c)for(c=t.split(Hi),u=c.length-1;a<u;a++)i+=c[a]+r[a];return i+c[u]},Hi=(function(){var s="(?:\\b(?:(?:rgb|rgba|hsl|hsla)\\(.+?\\))|\\B#(?:[0-9a-f]{3,4}){1,2}\\b",t;for(t in qo)s+="|"+t+"\\b";return new RegExp(s+")","gi")})(),H0=/hsl[a]?\(/,Uh=function(t){var e=t.join(" "),n;if(Hi.lastIndex=0,Hi.test(e))return n=H0.test(e),t[1]=mp(t[1],n),t[0]=mp(t[0],n,Vp(t[1])),!0},ta,Nn=(function(){var s=Date.now,t=500,e=33,n=s(),i=n,r=1e3/240,o=r,a=[],l,c,h,u,f,d,g=function _(m){var p=s()-i,S=m===!0,y,v,E,A;if((p>t||p<0)&&(n+=p-e),i+=p,E=i-n,y=E-o,(y>0||S)&&(A=++u.frame,f=E-u.time*1e3,u.time=E=E/1e3,o+=y+(y>=r?0:r-y),v=1),S||(l=c(_)),v)for(d=0;d<a.length;d++)a[d](E,f,A,m)};return u={time:0,frame:0,tick:function(){g(!0)},deltaRatio:function(m){return f/(1e3/(m||60))},wake:function(){yp&&(!_h&&Th()&&(Pi=_h=window,Ch=Pi.document||{},Xn.gsap=pn,(Pi.gsapVersions||(Pi.gsapVersions=[])).push(pn.version),Mp(nl||Pi.GreenSockGlobals||!Pi.gsap&&Pi||{}),Bp.forEach(kp)),h=typeof requestAnimationFrame<"u"&&requestAnimationFrame,l&&u.sleep(),c=h||function(m){return setTimeout(m,o-u.time*1e3+1|0)},ta=1,g(2))},sleep:function(){(h?cancelAnimationFrame:clearTimeout)(l),ta=0,c=jo},lagSmoothing:function(m,p){t=m||1/0,e=Math.min(p||33,t)},fps:function(m){r=1e3/(m||240),o=u.time*1e3+r},add:function(m,p,S){var y=p?function(v,E,A,T){m(v,E,A,T),u.remove(y)}:m;return u.remove(m),a[S?"unshift":"push"](y),Br(),y},remove:function(m,p){~(p=a.indexOf(m))&&a.splice(p,1)&&d>=p&&d--},_listeners:a},u})(),Br=function(){return!ta&&Nn.wake()},me={},G0=/^[\d.\-M][\d.\-,\s]/,W0=/["']/g,X0=function(t){for(var e={},n=t.substr(1,t.length-3).split(":"),i=n[0],r=1,o=n.length,a,l,c;r<o;r++)l=n[r],a=r!==o-1?l.lastIndexOf(","):l.length,c=l.substr(0,a),e[i]=isNaN(c)?c.replace(W0,"").trim():+c,i=l.substr(a+1).trim();return e},Y0=function(t){var e=t.indexOf("(")+1,n=t.indexOf(")"),i=t.indexOf("(",e);return t.substring(e,~i&&i<n?t.indexOf(")",n+1):n)},q0=function(t){var e=(t+"").split("("),n=me[e[0]];return n&&e.length>1&&n.config?n.config.apply(null,~t.indexOf("{")?[X0(e[1])]:Y0(t).split(",").map(Tp)):me._CE&&G0.test(t)?me._CE("",t):n},Z0=function(t){return function(e){return 1-t(1-e)}},Xs=function(t,e){return t&&(He(t)?t:me[t]||q0(t))||e},$s=function(t,e,n,i){n===void 0&&(n=function(l){return 1-e(1-l)}),i===void 0&&(i=function(l){return l<.5?e(l*2)/2:1-e((1-l)*2)/2});var r={easeIn:e,easeOut:n,easeInOut:i},o;return Tn(t,function(a){me[a]=Xn[a]=r,me[o=a.toLowerCase()]=n;for(var l in r)me[o+(l==="easeIn"?".in":l==="easeOut"?".out":".inOut")]=me[a+"."+l]=r[l]}),r},Hp=function(t){return function(e){return e<.5?(1-t(1-e*2))/2:.5+t((e-.5)*2)/2}},fh=function s(t,e,n){var i=e>=1?e:1,r=(n||(t?.3:.45))/(e<1?e:1),o=r/gh*(Math.asin(1/i)||0),a=function(h){return h===1?1:i*Math.pow(2,-10*h)*v0((h-o)*r)+1},l=t==="out"?a:t==="in"?function(c){return 1-a(1-c)}:Hp(a);return r=gh/r,l.config=function(c,h){return s(t,c,h)},l},dh=function s(t,e){e===void 0&&(e=1.70158);var n=function(o){return o?--o*o*((e+1)*o+e)+1:0},i=t==="out"?n:t==="in"?function(r){return 1-n(1-r)}:Hp(n);return i.config=function(r){return s(t,r)},i};Tn("Linear,Quad,Cubic,Quart,Quint,Strong",function(s,t){var e=t<5?t+1:t;$s(s+",Power"+(e-1),t?function(n){return Math.pow(n,e)}:function(n){return n},function(n){return 1-Math.pow(1-n,e)},function(n){return n<.5?Math.pow(n*2,e)/2:1-Math.pow((1-n)*2,e)/2})});me.Linear.easeNone=me.none=me.Linear.easeIn;$s("Elastic",fh("in"),fh("out"),fh());(function(s,t){var e=1/t,n=2*e,i=2.5*e,r=function(a){return a<e?s*a*a:a<n?s*Math.pow(a-1.5/t,2)+.75:a<i?s*(a-=2.25/t)*a+.9375:s*Math.pow(a-2.625/t,2)+.984375};$s("Bounce",function(o){return 1-r(1-o)},r)})(7.5625,2.75);$s("Expo",function(s){return Math.pow(2,10*(s-1))*s+s*s*s*s*s*s*(1-s)});$s("Circ",function(s){return-(vp(1-s*s)-1)});$s("Sine",function(s){return s===1?1:-_0(s*m0)+1});$s("Back",dh("in"),dh("out"),dh());me.SteppedEase=me.steps=Xn.SteppedEase={config:function(t,e){t===void 0&&(t=1);var n=1/t,i=t+(e?0:1),r=e?1:0,o=1-Ee;return function(a){return((i*ia(0,o,a)|0)+r)*n}}};Ko.ease=me["quad.out"];Tn("onComplete,onUpdate,onStart,onRepeat,onReverseComplete,onInterrupt",function(s){return Ph+=s+","+s+"Params,"});var Nh=function(t,e){this.id=g0++,t._gsap=this,this.target=t,this.harness=e,this.get=e?e.get:Lh,this.set=e?e.getSetter:pl},ea=(function(){function s(e){this.vars=e,this._delay=+e.delay||0,(this._repeat=e.repeat===1/0?-2:e.repeat||0)&&(this._rDelay=e.repeatDelay||0,this._yoyo=!!e.yoyo||!!e.yoyoEase),this._ts=1,Fr(this,+e.duration,1,1),this.data=e.data,Ne&&(this._ctx=Ne,Ne.data.push(this)),ta||Nn.wake()}var t=s.prototype;return t.delay=function(n){return n||n===0?(this.parent&&this.parent.smoothChildTiming&&this.startTime(this._start+n-this._delay),this._delay=n,this):this._delay},t.duration=function(n){return arguments.length?this.totalDuration(this._repeat>0?n+(n+this._rDelay)*this._repeat:n):this.totalDuration()&&this._dur},t.totalDuration=function(n){return arguments.length?(this._dirty=0,Fr(this,this._repeat<0?n:(n-this._repeat*this._rDelay)/(this._repeat+1))):this._tDur},t.totalTime=function(n,i){if(Br(),!arguments.length)return this._tTime;var r=this._dp;if(r&&r.smoothChildTiming&&this._ts){for(dl(this,n),!r._dp||r.parent||Cp(r,this);r&&r.parent;)r.parent._time!==r._start+(r._ts>=0?r._tTime/r._ts:(r.totalDuration()-r._tTime)/-r._ts)&&r.totalTime(r._tTime,!0),r=r.parent;!this.parent&&this._dp.autoRemoveChildren&&(this._ts>0&&n<this._tDur||this._ts<0&&n>0||!this._tDur&&!n)&&Ii(this._dp,this,this._start-this._delay)}return(this._tTime!==n||!this._dur&&!i||this._initted&&Math.abs(this._zTime)===Ee||!this._initted&&this._dur&&n||!n&&!this._initted&&(this.add||this._ptLookup))&&(this._ts||(this._pTime=n),wp(this,n,i)),this},t.time=function(n,i){return arguments.length?this.totalTime(Math.min(this.totalDuration(),n+fp(this))%(this._dur+this._rDelay)||(n?this._dur:0),i):this._time},t.totalProgress=function(n,i){return arguments.length?this.totalTime(this.totalDuration()*n,i):this.totalDuration()?Math.min(1,this._tTime/this._tDur):this.rawTime()>=0&&this._initted?1:0},t.progress=function(n,i){return arguments.length?this.totalTime(this.duration()*(this._yoyo&&!(this.iteration()&1)?1-n:n)+fp(this),i):this.duration()?Math.min(1,this._time/this._dur):this.rawTime()>0?1:0},t.iteration=function(n,i){var r=this.duration()+this._rDelay;return arguments.length?this.totalTime(this._time+(n-1)*r,i):this._repeat?Or(this._tTime,r)+1:1},t.timeScale=function(n,i){if(!arguments.length)return this._rts===-Ee?0:this._rts;if(this._rts===n)return this;var r=this.parent&&this._ts?rl(this.parent._time,this):this._tTime,o=this._rts<0;this._rts=+n||0,this._ts=this._ps||n===-Ee?0:this._rts;var a=this.totalDuration();return(o!==this._rts<0||r>0&&r<a)&&this.totalTime(ia(-Math.abs(this._delay),a,r),i!==!1),fl(this),C0(this)},t.paused=function(n){if(!arguments.length)return this._ps;if(this._ps!==n)if(this._ps=n,n)this._pTime=this._tTime||Math.max(-this._delay,this.rawTime()),this._ts=this._act=0;else{Br(),this._ts=this._rts;var i=this.parent&&!this.parent.smoothChildTiming?this.rawTime():this._tTime||this._pTime,r=this.progress()===1&&Math.abs(this._zTime)!==Ee,o;if(r)for(this._tTime-=Ee,o=this._first;o;){if(!o._dur&&o._zTime<0&&o._ts&&o._start<=i+Ee){r=!1;break}o=o._next}this.totalTime(i,r)}return this},t.startTime=function(n){if(arguments.length){this._start=Be(n);var i=this.parent||this._dp;return i&&(i._sort||!this.parent)&&Ii(i,this,this._start-this._delay),this}return this._start},t.endTime=function(n){return this._start+(On(n)?this.totalDuration():this.duration())/Math.abs(this._ts||1)},t.rawTime=function(n){var i=this.parent||this._dp;return i?n&&(!this._ts||this._repeat&&this._time&&this.totalProgress()<1)?this._tTime%(this._dur+this._rDelay):this._ts?rl(i.rawTime(n),this):this._tTime:this._tTime},t.revert=function(n){n===void 0&&(n=w0);var i=an;return an=n,Dh(this)&&(this.timeline&&this.timeline.revert(n),this.totalTime(-.01,n.suppressEvents)),this.data!=="nested"&&n.kill!==!1&&this.kill(),an=i,this},t.globalTime=function(n){for(var i=this,r=arguments.length?n:i.rawTime();i;)r=i._start+r/(Math.abs(i._ts)||1),i=i._dp;return!this.parent&&this._sat?this._sat.globalTime(n):r},t.repeat=function(n){return arguments.length?(this._repeat=n===1/0?-2:n,dp(this)):this._repeat===-2?1/0:this._repeat},t.repeatDelay=function(n){if(arguments.length){var i=this._time;return this._rDelay=n,dp(this),i?this.time(i):this}return this._rDelay},t.yoyo=function(n){return arguments.length?(this._yoyo=n,this):this._yoyo},t.seek=function(n,i){return this.totalTime(ai(this,n),On(i))},t.restart=function(n,i){return this.play().totalTime(n?-this._delay:0,On(i)),this._dur||(this._zTime=-Ee),this},t.play=function(n,i){return n!=null&&this.seek(n,i),this.reversed(!1).paused(!1)},t.reverse=function(n,i){return n!=null&&this.seek(n||this.totalDuration(),i),this.reversed(!0).paused(!1)},t.pause=function(n,i){return n!=null&&this.seek(n,i),this.paused(!0)},t.resume=function(){return this.paused(!1)},t.reversed=function(n){return arguments.length?(!!n!==this.reversed()&&this.timeScale(-this._rts||(n?-Ee:0)),this):this._rts<0},t.invalidate=function(){return this._initted=this._act=0,this._zTime=-Ee,this},t.isActive=function(){var n=this.parent||this._dp,i=this._start,r;return!!(!n||this._ts&&this._initted&&n.isActive()&&(r=n.rawTime(!0))>=i&&r<this.endTime(!0)-Ee)},t.eventCallback=function(n,i,r){var o=this.vars;return arguments.length>1?(i?(o[n]=i,r&&(o[n+"Params"]=r),n==="onUpdate"&&(this._onUpdate=i)):delete o[n],this):o[n]},t.then=function(n){var i=this,r=i._prom;return new Promise(function(o){var a=He(n)?n:Ep,l=function(){var h=i.then;i.then=null,r&&r(),He(a)&&(a=a(i))&&(a.then||a===i)&&(i.then=h),o(a),i.then=h};i._initted&&i.totalProgress()===1&&i._ts>=0||!i._tTime&&i._ts<0?l():i._prom=l})},t.kill=function(){Yo(this)},s})();Yn(ea.prototype,{_time:0,_start:0,_end:0,_tTime:0,_tDur:0,_dirty:0,_repeat:0,_yoyo:!1,parent:null,_initted:!1,_rDelay:0,_ts:1,_dp:0,ratio:0,_zTime:-Ee,_prom:0,_ps:!1,_rts:1});var fn=(function(s){_p(t,s);function t(n,i){var r;return n===void 0&&(n={}),r=s.call(this,n)||this,r.labels={},r.smoothChildTiming=!!n.smoothChildTiming,r.autoRemoveChildren=!!n.autoRemoveChildren,r._sort=On(n.sortChildren),ke&&Ii(n.parent||ke,Vi(r),i),n.reversed&&r.reverse(),n.paused&&r.paused(!0),n.scrollTrigger&&Rp(Vi(r),n.scrollTrigger),r}var e=t.prototype;return e.to=function(i,r,o){return $o(0,arguments,this),this},e.from=function(i,r,o){return $o(1,arguments,this),this},e.fromTo=function(i,r,o,a){return $o(2,arguments,this),this},e.set=function(i,r,o){return r.duration=0,r.parent=this,Zo(r).repeatDelay||(r.repeat=0),r.immediateRender=!!r.immediateRender,new Xe(i,r,ai(this,o),1),this},e.call=function(i,r,o){return Ii(this,Xe.delayedCall(0,i,r),o)},e.staggerTo=function(i,r,o,a,l,c,h){return o.duration=r,o.stagger=o.stagger||a,o.onComplete=c,o.onCompleteParams=h,o.parent=this,new Xe(i,o,ai(this,l)),this},e.staggerFrom=function(i,r,o,a,l,c,h){return o.runBackwards=1,Zo(o).immediateRender=On(o.immediateRender),this.staggerTo(i,r,o,a,l,c,h)},e.staggerFromTo=function(i,r,o,a,l,c,h,u){return a.startAt=o,Zo(a).immediateRender=On(a.immediateRender),this.staggerTo(i,r,a,l,c,h,u)},e.render=function(i,r,o){var a=this._time,l=this._dirty?this.totalDuration():this._tDur,c=this._dur,h=i<=0?0:Be(i),u=this._zTime<0!=i<0&&(this._initted||!c),f,d,g,_,m,p,S,y,v,E,A,T;if(this!==ke&&h>l&&i>=0&&(h=l),h!==this._tTime||o||u){if(a!==this._time&&c&&(h+=this._time-a,i+=this._time-a),f=h,v=this._start,y=this._ts,p=!y,u&&(c||(a=this._zTime),(i||!r)&&(this._zTime=i)),this._repeat){if(A=this._yoyo,m=c+this._rDelay,this._repeat<-1&&i<0)return this.totalTime(m*100+i,r,o);if(f=Be(h%m),h===l?(_=this._repeat,f=c):(E=Be(h/m),_=~~E,_&&_===E&&(f=c,_--),f>c&&(f=c)),E=Or(this._tTime,m),!a&&this._tTime&&E!==_&&this._tTime-E*m-this._dur<=0&&(E=_),A&&_&1&&(f=c-f,T=1),_!==E&&!this._lock){var R=A&&E&1,M=R===(A&&_&1);if(_<E&&(R=!R),a=R?0:h%c?c:h,this._lock=1,this.render(a||(T?0:Be(_*m)),r,!c)._lock=0,this._tTime=h,!r&&this.parent&&Wn(this,"onRepeat"),this.vars.repeatRefresh&&!T&&(this.invalidate()._lock=1,E=_),a&&a!==this._time||p!==!this._ts||this.vars.onRepeat&&!this.parent&&!this._act)return this;if(c=this._dur,l=this._tDur,M&&(this._lock=2,a=R?c:-1e-4,this.render(a,!0),this.vars.repeatRefresh&&!T&&this.invalidate()),this._lock=0,!this._ts&&!p)return this}}if(this._hasPause&&!this._forcing&&this._lock<2&&(S=L0(this,Be(a),Be(f)),S&&(h-=f-(f=S._start))),this._tTime=h,this._time=f,this._act=!!y,this._initted||(this._onUpdate=this.vars.onUpdate,this._initted=1,this._zTime=i,a=0),!a&&h&&c&&!r&&!E&&(Wn(this,"onStart"),this._tTime!==h))return this;if(f>=a&&i>=0)for(d=this._first;d;){if(g=d._next,(d._act||f>=d._start)&&d._ts&&S!==d){if(d.parent!==this)return this.render(i,r,o);if(d.render(d._ts>0?(f-d._start)*d._ts:(d._dirty?d.totalDuration():d._tDur)+(f-d._start)*d._ts,r,o),f!==this._time||!this._ts&&!p){S=0,g&&(h+=this._zTime=-Ee);break}}d=g}else{d=this._last;for(var x=i<0?i:f;d;){if(g=d._prev,(d._act||x<=d._end)&&d._ts&&S!==d){if(d.parent!==this)return this.render(i,r,o);if(d.render(d._ts>0?(x-d._start)*d._ts:(d._dirty?d.totalDuration():d._tDur)+(x-d._start)*d._ts,r,o||an&&Dh(d)),f!==this._time||!this._ts&&!p){S=0,g&&(h+=this._zTime=x?-Ee:Ee);break}}d=g}}if(S&&!r&&(this.pause(),S.render(f>=a?0:-Ee)._zTime=f>=a?1:-1,this._ts))return this._start=v,fl(this),this.render(i,r,o);this._onUpdate&&!r&&Wn(this,"onUpdate",!0),(h===l&&this._tTime>=this.totalDuration()||!h&&a)&&(v===this._start||Math.abs(y)!==Math.abs(this._ts))&&(this._lock||((i||!c)&&(h===l&&this._ts>0||!h&&this._ts<0)&&_s(this,1),!r&&!(i<0&&!a)&&(h||a||!l)&&(Wn(this,h===l&&i>=0?"onComplete":"onReverseComplete",!0),this._prom&&!(h<l&&this.timeScale()>0)&&this._prom())))}return this},e.add=function(i,r){var o=this;if(Gi(r)||(r=ai(this,r,i)),!(i instanceof ea)){if(dn(i))return i.forEach(function(a){return o.add(a,r)}),this;if(Ke(i))return this.addLabel(i,r);if(He(i))i=Xe.delayedCall(0,i);else return this}return this!==i?Ii(this,i,r):this},e.getChildren=function(i,r,o,a){i===void 0&&(i=!0),r===void 0&&(r=!0),o===void 0&&(o=!0),a===void 0&&(a=-li);for(var l=[],c=this._first;c;)c._start>=a&&(c instanceof Xe?r&&l.push(c):(o&&l.push(c),i&&l.push.apply(l,c.getChildren(!0,r,o)))),c=c._next;return l},e.getById=function(i){for(var r=this.getChildren(1,1,1),o=r.length;o--;)if(r[o].vars.id===i)return r[o]},e.remove=function(i){return Ke(i)?this.removeLabel(i):He(i)?this.killTweensOf(i):(i.parent===this&&ul(this,i),i===this._recent&&(this._recent=this._last),Ws(this))},e.totalTime=function(i,r){return arguments.length?(this._forcing=1,!this._dp&&this._ts&&(this._start=Be(Nn.time-(this._ts>0?i/this._ts:(this.totalDuration()-i)/-this._ts))),s.prototype.totalTime.call(this,i,r),this._forcing=0,this):this._tTime},e.addLabel=function(i,r){return this.labels[i]=ai(this,r),this},e.removeLabel=function(i){return delete this.labels[i],this},e.addPause=function(i,r,o){var a=Xe.delayedCall(0,r||jo,o);return a.data="isPause",this._hasPause=1,Ii(this,a,ai(this,i))},e.removePause=function(i){var r=this._first;for(i=ai(this,i);r;)r._start===i&&r.data==="isPause"&&_s(r),r=r._next},e.killTweensOf=function(i,r,o){for(var a=this.getTweensOf(i,o),l=a.length;l--;)ps!==a[l]&&a[l].kill(i,r);return this},e.getTweensOf=function(i,r){for(var o=[],a=ci(i),l=this._first,c=Gi(r),h;l;)l instanceof Xe?T0(l._targets,a)&&(c?(!ps||l._initted&&l._ts)&&l.globalTime(0)<=r&&l.globalTime(l.totalDuration())>r:!r||l.isActive())&&o.push(l):(h=l.getTweensOf(a,r)).length&&o.push.apply(o,h),l=l._next;return o},e.tweenTo=function(i,r){r=r||{};var o=this,a=ai(o,i),l=r,c=l.startAt,h=l.onStart,u=l.onStartParams,f=l.immediateRender,d,g=Xe.to(o,Yn({ease:r.ease||"none",lazy:!1,immediateRender:!1,time:a,overwrite:"auto",duration:r.duration||Math.abs((a-(c&&"time"in c?c.time:o._time))/o.timeScale())||Ee,onStart:function(){if(o.pause(),!d){var m=r.duration||Math.abs((a-(c&&"time"in c?c.time:o._time))/o.timeScale());g._dur!==m&&Fr(g,m,0,1).render(g._time,!0,!0),d=1}h&&h.apply(g,u||[])}},r));return f?g.render(0):g},e.tweenFromTo=function(i,r,o){return this.tweenTo(r,Yn({startAt:{time:ai(this,i)}},o))},e.recent=function(){return this._recent},e.nextLabel=function(i){return i===void 0&&(i=this._time),pp(this,ai(this,i))},e.previousLabel=function(i){return i===void 0&&(i=this._time),pp(this,ai(this,i),1)},e.currentLabel=function(i){return arguments.length?this.seek(i,!0):this.previousLabel(this._time+Ee)},e.shiftChildren=function(i,r,o){o===void 0&&(o=0);var a=this._first,l=this.labels,c;for(i=Be(i);a;)a._start>=o&&(a._start+=i,a._end+=i),a=a._next;if(r)for(c in l)l[c]>=o&&(l[c]+=i);return Ws(this)},e.invalidate=function(i){var r=this._first;for(this._lock=0;r;)r.invalidate(i),r=r._next;return s.prototype.invalidate.call(this,i)},e.clear=function(i){i===void 0&&(i=!0);for(var r=this._first,o;r;)o=r._next,this.remove(r),r=o;return this._dp&&(this._time=this._tTime=this._pTime=0),i&&(this.labels={}),Ws(this)},e.totalDuration=function(i){var r=0,o=this,a=o._last,l=li,c,h,u;if(arguments.length)return o.timeScale((o._repeat<0?o.duration():o.totalDuration())/(o.reversed()?-i:i));if(o._dirty){for(u=o.parent;a;)c=a._prev,a._dirty&&a.totalDuration(),h=a._start,h>l&&o._sort&&a._ts&&!o._lock?(o._lock=1,Ii(o,a,h-a._delay,1)._lock=0):l=h,h<0&&a._ts&&(r-=h,(!u&&!o._dp||u&&u.smoothChildTiming)&&(o._start+=Be(h/o._ts),o._time-=h,o._tTime-=h),o.shiftChildren(-h,!1,-1/0),l=0),a._end>r&&a._ts&&(r=a._end),a=c;Fr(o,o===ke&&o._time>r?o._time:r,1,1),o._dirty=0}return o._tDur},t.updateRoot=function(i){if(ke._ts&&(wp(ke,rl(i,ke)),bp=Nn.frame),Nn.frame>=hp){hp+=Fn.autoSleep||120;var r=ke._first;if((!r||!r._ts)&&Fn.autoSleep&&Nn._listeners.length<2){for(;r&&!r._ts;)r=r._next;r||Nn.sleep()}}},t})(ea);Yn(fn.prototype,{_lock:0,_hasPause:0,_forcing:0});var $0=function(t,e,n,i,r,o,a){var l=new En(this._pt,t,e,0,1,zh,null,r),c=0,h=0,u,f,d,g,_,m,p,S;for(l.b=n,l.e=i,n+="",i+="",(p=~i.indexOf("random("))&&(i=kr(i)),o&&(S=[n,i],o(S,t,e),n=S[0],i=S[1]),f=n.match(ch)||[];u=ch.exec(i);)g=u[0],_=i.substring(c,u.index),d?d=(d+1)%5:_.substr(-5)==="rgba("&&(d=1),g!==f[h++]&&(m=parseFloat(f[h-1])||0,l._pt={_next:l._pt,p:_||h===1?_:",",s:m,c:g.charAt(1)==="="?Zs(m,g)-m:parseFloat(g)-m,m:d&&d<4?Math.round:0},c=ch.lastIndex);return l.c=c<i.length?i.substring(c,i.length):"",l.fp=a,(Ah.test(i)||p)&&(l.e=0),this._pt=l,l},Oh=function(t,e,n,i,r,o,a,l,c,h){He(i)&&(i=i(r||0,t,o));var u=t[e],f=n!=="get"?n:He(u)?c?t[e.indexOf("set")||!He(t["get"+e.substr(3)])?e:"get"+e.substr(3)](c):t[e]():u,d=He(u)?c?tv:Wp:kh,g;if(Ke(i)&&(~i.indexOf("random(")&&(i=kr(i)),i.charAt(1)==="="&&(g=Zs(f,i)+(ln(f)||0),(g||g===0)&&(i=g))),!h||f!==i||bh)return!isNaN(f*i)&&i!==""?(g=new En(this._pt,t,e,+f||0,i-(f||0),typeof u=="boolean"?nv:Xp,0,d),c&&(g.fp=c),a&&g.modifier(a,this,t),this._pt=g):(!u&&!(e in t)&&hl(e,i),$0.call(this,t,e,f,i,d,l||Fn.stringFilter,c))},J0=function(t,e,n,i,r){if(He(t)&&(t=Jo(t,r,e,n,i)),!Li(t)||t.style&&t.nodeType||dn(t)||xp(t))return Ke(t)?Jo(t,r,e,n,i):t;var o={},a;for(a in t)o[a]=Jo(t[a],r,e,n,i);return o},Fh=function(t,e,n,i,r,o){var a,l,c,h;if(Un[t]&&(a=new Un[t]).init(r,a.rawVars?e[t]:J0(e[t],i,r,o,n),n,i,o)!==!1&&(n._pt=l=new En(n._pt,r,t,0,1,a.render,a,0,a.priority),n!==Ur))for(c=n._ptLookup[n._targets.indexOf(r)],h=a._props.length;h--;)c[a._props[h]]=l;return a},ps,bh,Bh=function s(t,e,n){var i=t.vars,r=i.ease,o=i.startAt,a=i.immediateRender,l=i.lazy,c=i.onUpdate,h=i.runBackwards,u=i.yoyoEase,f=i.keyframes,d=i.autoRevert,g=t._dur,_=t._startAt,m=t._targets,p=t.parent,S=p&&p.data==="nested"?p.vars.targets:m,y=t._overwrite==="auto"&&!wh,v=t.timeline,E=i.easeReverse||u,A,T,R,M,x,L,U,F,z,q,H,W,V;if(v&&(!f||!r)&&(r="none"),t._ease=Xs(r,Ko.ease),t._rEase=E&&(Xs(E)||t._ease),t._from=!v&&!!i.runBackwards,t._from&&(t.ratio=1),!v||f&&!i.stagger){if(F=m[0]?gs(m[0]).harness:0,W=F&&i[F.prop],A=sl(i,Rh),_&&(_._zTime<0&&_.progress(1),e<0&&h&&a&&!d?_.render(-1,!0):_.revert(h&&g?ja:b0),_._lazy=0),o){if(_s(t._startAt=Xe.set(m,Yn({data:"isStart",overwrite:!1,parent:p,immediateRender:!0,lazy:!_&&On(l),startAt:null,delay:0,onUpdate:c&&function(){return Wn(t,"onUpdate")},stagger:0},o))),t._startAt._dp=0,t._startAt._sat=t,e<0&&(an||!a&&!d)&&t._startAt.revert(ja),a&&g&&e<=0&&n<=0){e&&(t._zTime=e);return}}else if(h&&g&&!_){if(e&&(a=!1),R=Yn({overwrite:!1,data:"isFromStart",lazy:a&&!_&&On(l),immediateRender:a,stagger:0,parent:p},A),W&&(R[F.prop]=W),_s(t._startAt=Xe.set(m,R)),t._startAt._dp=0,t._startAt._sat=t,e<0&&(an?t._startAt.revert(ja):t._startAt.render(-1,!0)),t._zTime=e,!a)s(t._startAt,Ee,Ee);else if(!e)return}for(t._pt=t._ptCache=0,l=g&&On(l)||l&&!g,T=0;T<m.length;T++){if(x=m[T],U=x._gsap||Ih(m)[T]._gsap,t._ptLookup[T]=q={},vh[U.id]&&ms.length&&il(),H=S===m?T:S.indexOf(x),F&&(z=new F).init(x,W||A,t,H,S)!==!1&&(t._pt=M=new En(t._pt,x,z.name,0,1,z.render,z,0,z.priority),z._props.forEach(function(st){q[st]=M}),z.priority&&(L=1)),!F||W)for(R in A)Un[R]&&(z=Fh(R,A,t,H,x,S))?z.priority&&(L=1):q[R]=M=Oh.call(t,x,R,"get",A[R],H,S,0,i.stringFilter);t._op&&t._op[T]&&t.kill(x,t._op[T]),y&&t._pt&&(ps=t,ke.killTweensOf(x,q,t.globalTime(e)),V=!t.parent,ps=0),t._pt&&l&&(vh[U.id]=1)}L&&Hh(t),t._onInit&&t._onInit(t)}t._onUpdate=c,t._initted=(!t._op||t._pt)&&!V,f&&e<=0&&v.render(li,!0,!0)},K0=function(t,e,n,i,r,o,a,l){var c=(t._pt&&t._ptCache||(t._ptCache={}))[e],h,u,f,d;if(!c)for(c=t._ptCache[e]=[],f=t._ptLookup,d=t._targets.length;d--;){if(h=f[d][e],h&&h.d&&h.d._pt)for(h=h.d._pt;h&&h.p!==e&&h.fp!==e;)h=h._next;if(!h)return bh=1,t.vars[e]="+=0",Bh(t,a),bh=0,l?Qo(e+" not eligible for reset. Try splitting into individual properties"):1;c.push(h)}for(d=c.length;d--;)u=c[d],h=u._pt||u,h.s=(i||i===0)&&!r?i:h.s+(i||0)+o*h.c,h.c=n-h.s,u.e&&(u.e=Ge(n)+ln(u.e)),u.b&&(u.b=h.s+ln(u.b))},Q0=function(t,e){var n=t[0]?gs(t[0]).harness:0,i=n&&n.aliases,r,o,a,l;if(!i)return e;r=Nr({},e);for(o in i)if(o in r)for(l=i[o].split(","),a=l.length;a--;)r[l[a]]=r[o];return r},j0=function(t,e,n,i){var r=e.ease||i||"power1.inOut",o,a;if(dn(e))a=n[t]||(n[t]=[]),e.forEach(function(l,c){return a.push({t:c/(e.length-1)*100,v:l,e:r})});else for(o in e)a=n[o]||(n[o]=[]),o==="ease"||a.push({t:parseFloat(t),v:e[o],e:r})},Jo=function(t,e,n,i,r){return He(t)?t.call(e,n,i,r):Ke(t)&&~t.indexOf("random(")?kr(t):t},al=Ph+"repeat,repeatDelay,yoyo,repeatRefresh,yoyoEase,easeReverse,autoRevert",Gp={};Tn(al+",id,stagger,delay,duration,paused,scrollTrigger",function(s){return Gp[s]=1});al=al.split(",");var Xe=(function(s){_p(t,s);function t(n,i,r,o){var a;typeof i=="number"&&(r.duration=i,i=r,r=null),a=s.call(this,o?i:Zo(i))||this;var l=a.vars,c=l.duration,h=l.delay,u=l.immediateRender,f=l.stagger,d=l.overwrite,g=l.keyframes,_=l.defaults,m=l.scrollTrigger,p=i.parent||ke,S=(dn(n)||xp(n)?Gi(n[0]):"length"in i)?[n]:ci(n),y,v,E,A,T,R,M,x;if(a._targets=S.length?Ih(S):Qo("GSAP target "+n+" not found. https://gsap.com",!Fn.nullTargetWarn)||[],a._ptLookup=[],a._overwrite=d,g||f||Qa(c)||Qa(h)){i=a.vars;var L=i.easeReverse||i.yoyoEase;if(y=a.timeline=new fn({data:"nested",defaults:_||{},targets:p&&p.data==="nested"?p.vars.targets:S}),y.kill(),y.parent=y._dp=Vi(a),y._start=0,f||Qa(c)||Qa(h)){if(A=S.length,M=f&&Dp(f),Li(f))for(T in f)~al.indexOf(T)&&(x||(x={}),x[T]=f[T]);for(v=0;v<A;v++)E=sl(i,Gp),E.stagger=0,L&&(E.easeReverse=L),x&&Nr(E,x),R=S[v],E.duration=+Jo(c,Vi(a),v,R,S),E.delay=(+Jo(h,Vi(a),v,R,S)||0)-a._delay,!f&&A===1&&E.delay&&(a._delay=h=E.delay,a._start+=h,E.delay=0),y.to(R,E,M?M(v,R,S):0),y._ease=me.none;y.duration()?c=h=0:a.timeline=0}else if(g){Zo(Yn(y.vars.defaults,{ease:"none"})),y._ease=Xs(g.ease||i.ease||"none");var U=0,F,z,q;if(dn(g))g.forEach(function(H){return y.to(S,H,">")}),y.duration();else{E={};for(T in g)T==="ease"||T==="easeEach"||j0(T,g[T],E,g.easeEach);for(T in E)for(F=E[T].sort(function(H,W){return H.t-W.t}),U=0,v=0;v<F.length;v++)z=F[v],q={ease:z.e,duration:(z.t-(v?F[v-1].t:0))/100*c},q[T]=z.v,y.to(S,q,U),U+=q.duration;y.duration()<c&&y.to({},{duration:c-y.duration()})}}c||a.duration(c=y.duration())}else a.timeline=0;return d===!0&&!wh&&(ps=Vi(a),ke.killTweensOf(S),ps=0),Ii(p,Vi(a),r),i.reversed&&a.reverse(),i.paused&&a.paused(!0),(u||!c&&!g&&a._start===Be(p._time)&&On(u)&&R0(Vi(a))&&p.data!=="nested")&&(a._tTime=-Ee,a.render(Math.max(0,-h)||0)),m&&Rp(Vi(a),m),a}var e=t.prototype;return e.render=function(i,r,o){var a=this._time,l=this._tDur,c=this._dur,h=i<0,u=i>l-Ee&&!h?l:i<Ee?0:i,f,d,g,_,m,p,S,y;if(!c)I0(this,i,r,o);else if(u!==this._tTime||!i||o||!this._initted&&this._tTime||this._startAt&&this._zTime<0!==h||this._lazy){if(f=u,y=this.timeline,this._repeat){if(_=c+this._rDelay,this._repeat<-1&&h)return this.totalTime(_*100+i,r,o);if(f=Be(u%_),u===l?(g=this._repeat,f=c):(m=Be(u/_),g=~~m,g&&g===m?(f=c,g--):f>c&&(f=c)),p=this._yoyo&&g&1,p&&(f=c-f),m=Or(this._tTime,_),f===a&&!o&&this._initted&&g===m)return this._tTime=u,this;g!==m&&this.vars.repeatRefresh&&!p&&!this._lock&&f!==_&&this._initted&&(this._lock=o=1,this.render(Be(_*g),!0).invalidate()._lock=0)}if(!this._initted){if(Pp(this,h?i:f,o,r,u))return this._tTime=0,this;if(a!==this._time&&!(o&&this.vars.repeatRefresh&&g!==m))return this;if(c!==this._dur)return this.render(i,r,o)}if(this._rEase){var v=f<a;if(v!==this._inv){var E=v?a:c-a;this._inv=v,this._from&&(this.ratio=1-this.ratio),this._invRatio=this.ratio,this._invTime=a,this._invRecip=E?(v?-1:1)/E:0,this._invScale=v?-this.ratio:1-this.ratio,this._invEase=v?this._rEase:this._ease}this.ratio=S=this._invRatio+this._invScale*this._invEase((f-this._invTime)*this._invRecip)}else this.ratio=S=this._ease(f/c);if(this._from&&(this.ratio=S=1-S),this._tTime=u,this._time=f,!this._act&&this._ts&&(this._act=1,this._lazy=0),!a&&u&&!r&&!m&&(Wn(this,"onStart"),this._tTime!==u))return this;for(d=this._pt;d;)d.r(S,d.d),d=d._next;y&&y.render(i<0?i:y._dur*y._ease(f/this._dur),r,o)||this._startAt&&(this._zTime=i),this._onUpdate&&!r&&(h&&xh(this,i,r,o),Wn(this,"onUpdate")),this._repeat&&g!==m&&this.vars.onRepeat&&!r&&this.parent&&Wn(this,"onRepeat"),(u===this._tDur||!u)&&this._tTime===u&&(h&&!this._onUpdate&&xh(this,i,!0,!0),(i||!c)&&(u===this._tDur&&this._ts>0||!u&&this._ts<0)&&_s(this,1),!r&&!(h&&!a)&&(u||a||p)&&(Wn(this,u===l?"onComplete":"onReverseComplete",!0),this._prom&&!(u<l&&this.timeScale()>0)&&this._prom()))}return this},e.targets=function(){return this._targets},e.invalidate=function(i){return(!i||!this.vars.runBackwards)&&(this._startAt=0),this._pt=this._op=this._onUpdate=this._lazy=this.ratio=0,this._ptLookup=[],this.timeline&&this.timeline.invalidate(i),s.prototype.invalidate.call(this,i)},e.resetTo=function(i,r,o,a,l){ta||Nn.wake(),this._ts||this.play();var c=Math.min(this._dur,(this._dp._time-this._start)*this._ts),h;return this._initted||Bh(this,c),h=this._ease(c/this._dur),K0(this,i,r,o,a,h,c,l)?this.resetTo(i,r,o,a,1):(dl(this,0),this.parent||Ap(this._dp,this,"_first","_last",this._dp._sort?"_start":0),this.render(0))},e.kill=function(i,r){if(r===void 0&&(r="all"),!i&&(!r||r==="all"))return this._lazy=this._pt=0,this.parent?Yo(this):this.scrollTrigger&&this.scrollTrigger.kill(!!an),this;if(this.timeline){var o=this.timeline.totalDuration();return this.timeline.killTweensOf(i,r,ps&&ps.vars.overwrite!==!0)._first||Yo(this),this.parent&&o!==this.timeline.totalDuration()&&Fr(this,this._dur*this.timeline._tDur/o,0,1),this}var a=this._targets,l=i?ci(i):a,c=this._ptLookup,h=this._pt,u,f,d,g,_,m,p;if((!r||r==="all")&&A0(a,l))return r==="all"&&(this._pt=0),Yo(this);for(u=this._op=this._op||[],r!=="all"&&(Ke(r)&&(_={},Tn(r,function(S){return _[S]=1}),r=_),r=Q0(a,r)),p=a.length;p--;)if(~l.indexOf(a[p])){f=c[p],r==="all"?(u[p]=r,g=f,d={}):(d=u[p]=u[p]||{},g=r);for(_ in g)m=f&&f[_],m&&((!("kill"in m.d)||m.d.kill(_)===!0)&&ul(this,m,"_pt"),delete f[_]),d!=="all"&&(d[_]=1)}return this._initted&&!this._pt&&h&&Yo(this),this},t.to=function(i,r){return new t(i,r,arguments[2])},t.from=function(i,r){return $o(1,arguments)},t.delayedCall=function(i,r,o,a){return new t(r,0,{immediateRender:!1,lazy:!1,overwrite:!1,delay:i,onComplete:r,onReverseComplete:r,onCompleteParams:o,onReverseCompleteParams:o,callbackScope:a})},t.fromTo=function(i,r,o){return $o(2,arguments)},t.set=function(i,r){return r.duration=0,r.repeatDelay||(r.repeat=0),new t(i,r)},t.killTweensOf=function(i,r,o){return ke.killTweensOf(i,r,o)},t})(ea);Yn(Xe.prototype,{_targets:[],_lazy:0,_startAt:0,_op:0,_onInit:0});Tn("staggerTo,staggerFrom,staggerFromTo",function(s){Xe[s]=function(){var t=new fn,e=yh.call(arguments,0);return e.splice(s==="staggerFromTo"?5:4,0,0),t[s].apply(t,e)}});var kh=function(t,e,n){return t[e]=n},Wp=function(t,e,n){return t[e](n)},tv=function(t,e,n,i){return t[e](i.fp,n)},ev=function(t,e,n){return t.setAttribute(e,n)},pl=function(t,e){return He(t[e])?Wp:cl(t[e])&&t.setAttribute?ev:kh},Xp=function(t,e){return e.set(e.t,e.p,Math.round((e.s+e.c*t)*1e6)/1e6,e)},nv=function(t,e){return e.set(e.t,e.p,!!(e.s+e.c*t),e)},zh=function(t,e){var n=e._pt,i="";if(!t&&e.b)i=e.b;else if(t===1&&e.e)i=e.e;else{for(;n;)i=n.p+(n.m?n.m(n.s+n.c*t):Math.round((n.s+n.c*t)*1e4)/1e4)+i,n=n._next;i+=e.c}e.set(e.t,e.p,i,e)},Vh=function(t,e){for(var n=e._pt;n;)n.r(t,n.d),n=n._next},iv=function(t,e,n,i){for(var r=this._pt,o;r;)o=r._next,r.p===i&&r.modifier(t,e,n),r=o},sv=function(t){for(var e=this._pt,n,i;e;)i=e._next,e.p===t&&!e.op||e.op===t?ul(this,e,"_pt"):e.dep||(n=1),e=i;return!n},rv=function(t,e,n,i){i.mSet(t,e,i.m.call(i.tween,n,i.mt),i)},Hh=function(t){for(var e=t._pt,n,i,r,o;e;){for(n=e._next,i=r;i&&i.pr>e.pr;)i=i._next;(e._prev=i?i._prev:o)?e._prev._next=e:r=e,(e._next=i)?i._prev=e:o=e,e=n}t._pt=r},En=(function(){function s(e,n,i,r,o,a,l,c,h){this.t=n,this.s=r,this.c=o,this.p=i,this.r=a||Xp,this.d=l||this,this.set=c||kh,this.pr=h||0,this._next=e,e&&(e._prev=this)}var t=s.prototype;return t.modifier=function(n,i,r){this.mSet=this.mSet||this.set,this.set=rv,this.m=n,this.mt=r,this.tween=i},s})();Tn(Ph+"parent,duration,ease,delay,overwrite,runBackwards,startAt,yoyo,immediateRender,repeat,repeatDelay,data,paused,reversed,lazy,callbackScope,stringFilter,id,yoyoEase,stagger,inherit,repeatRefresh,keyframes,autoRevert,scrollTrigger,easeReverse",function(s){return Rh[s]=1});Xn.TweenMax=Xn.TweenLite=Xe;Xn.TimelineLite=Xn.TimelineMax=fn;ke=new fn({sortChildren:!1,defaults:Ko,autoRemoveChildren:!0,id:"root",smoothChildTiming:!0});Fn.stringFilter=Uh;var Ys=[],el={},ov=[],gp=0,av=0,ph=function(t){return(el[t]||ov).map(function(e){return e()})},na=function(){var t=Date.now(),e=[];t-gp>2&&(ph("matchMediaInit"),Ys.forEach(function(n){var i=n.queries,r=n.conditions,o,a,l,c;for(a in i)o=Pi.matchMedia(i[a]).matches,o&&(l=1),o!==r[a]&&(r[a]=o,c=1);c&&(n.revert(),l&&e.push(n))}),ph("matchMediaRevert"),e.forEach(function(n){return n.onMatch(n,function(i){return n.add(null,i)})}),gp=t,ph("matchMedia"))},Yp=(function(){function s(e,n){this.selector=n&&Mh(n),this.data=[],this._r=[],this.isReverted=!1,this.id=av++,e&&this.add(e)}var t=s.prototype;return t.add=function(n,i,r){He(n)&&(r=i,i=n,n=He);var o=this,a=function(){var c=Ne,h=o.selector,u;return c&&c!==o&&c.data.push(o),r&&(o.selector=Mh(r)),Ne=o,u=i.apply(o,arguments),He(u)&&o._r.push(u),Ne=c,o.selector=h,o.isReverted=!1,u};return o.last=a,n===He?a(o,function(l){return o.add(null,l)}):n?o[n]=a:a},t.ignore=function(n){var i=Ne;Ne=null,n(this),Ne=i},t.getTweens=function(){var n=[];return this.data.forEach(function(i){return i instanceof s?n.push.apply(n,i.getTweens()):i instanceof Xe&&!(i.parent&&i.parent.data==="nested")&&n.push(i)}),n},t.clear=function(){this._r.length=this.data.length=0},t.kill=function(n,i){var r=this;if(n?(function(){for(var a=r.getTweens(),l=r.data.length,c;l--;)c=r.data[l],c.data==="isFlip"&&(c.revert(),c.getChildren(!0,!0,!1).forEach(function(h){return a.splice(a.indexOf(h),1)}));for(a.map(function(h){return{g:h._dur||h._delay||h._sat&&!h._sat.vars.immediateRender?h.globalTime(0):-1/0,t:h}}).sort(function(h,u){return u.g-h.g||-1/0}).forEach(function(h){return h.t.revert(n)}),l=r.data.length;l--;)c=r.data[l],c instanceof fn?c.data!=="nested"&&(c.scrollTrigger&&c.scrollTrigger.revert(),c.kill()):!(c instanceof Xe)&&c.revert&&c.revert(n);r._r.forEach(function(h){return h(n,r)}),r.isReverted=!0})():this.data.forEach(function(a){return a.kill&&a.kill()}),this.clear(),i){for(var o=Ys.length;o--;)Ys[o].id===this.id&&Ys.splice(o,1);this._mqs&&this._mqs.forEach(function(a){return a.removeListener?a.removeListener(na):a.removeEventListener("change",na)}),this._mqs=null}},t.revert=function(n){this.kill(n||{})},s})(),lv=(function(){function s(e){this.contexts=[],this.scope=e,Ne&&Ne.data.push(this)}var t=s.prototype;return t.add=function(n,i,r){Li(n)||(n={matches:n});var o=new Yp(0,r||this.scope),a=o.conditions={},l,c,h;Ne&&!o.selector&&(o.selector=Ne.selector),this.contexts.push(o),i=o.add("onMatch",i),o.queries=n;for(c in n)c==="all"?h=1:(l=Pi.matchMedia(n[c]),l&&(Ys.indexOf(o)<0&&Ys.push(o),(a[c]=l.matches)&&(h=1),l.addListener?l.addListener(na):l.addEventListener("change",na),(o._mqs||(o._mqs=[])).push(l)));return h&&i(o,function(u){return o.add(null,u)}),this},t.revert=function(n){this.kill(n||{})},t.kill=function(n){this.contexts.forEach(function(i){return i.kill(n,!0)})},s})(),ll={registerPlugin:function(){for(var t=arguments.length,e=new Array(t),n=0;n<t;n++)e[n]=arguments[n];e.forEach(function(i){return kp(i)})},timeline:function(t){return new fn(t)},getTweensOf:function(t,e){return ke.getTweensOf(t,e)},getProperty:function(t,e,n,i){Ke(t)&&(t=ci(t)[0]);var r=gs(t||{}).get,o=n?Ep:Tp;return n==="native"&&(n=""),t&&(e?o((Un[e]&&Un[e].get||r)(t,e,n,i)):function(a,l,c){return o((Un[a]&&Un[a].get||r)(t,a,l,c))})},quickSetter:function(t,e,n){if(t=ci(t),t.length>1){var i=t.map(function(h){return pn.quickSetter(h,e,n)}),r=i.length;return function(h){for(var u=r;u--;)i[u](h)}}t=t[0]||{};var o=Un[e],a=gs(t),l=a.harness&&(a.harness.aliases||{})[e]||e,c=o?function(h){var u=new o;Ur._pt=0,u.init(t,n?h+n:h,Ur,0,[t]),u.render(1,u),Ur._pt&&Vh(1,Ur)}:a.set(t,l);return o?c:function(h){return c(t,l,n?h+n:h,a,1)}},quickTo:function(t,e,n){var i,r=pn.to(t,Yn((i={},i[e]="+=0.1",i.paused=!0,i.stagger=0,i),n||{})),o=function(l,c,h){return r.resetTo(e,l,c,h)};return o.tween=r,o},isTweening:function(t){return ke.getTweensOf(t,!0).length>0},defaults:function(t){return t&&t.ease&&(t.ease=Xs(t.ease,Ko.ease)),up(Ko,t||{})},config:function(t){return up(Fn,t||{})},registerEffect:function(t){var e=t.name,n=t.effect,i=t.plugins,r=t.defaults,o=t.extendTimeline;(i||"").split(",").forEach(function(a){return a&&!Un[a]&&!Xn[a]&&Qo(e+" effect requires "+a+" plugin.")}),hh[e]=function(a,l,c){return n(ci(a),Yn(l||{},r),c)},o&&(fn.prototype[e]=function(a,l,c){return this.add(hh[e](a,Li(l)?l:(c=l)&&{},this),c)})},registerEase:function(t,e){me[t]=Xs(e)},parseEase:function(t,e){return arguments.length?Xs(t,e):me},getById:function(t){return ke.getById(t)},exportRoot:function(t,e){t===void 0&&(t={});var n=new fn(t),i,r;for(n.smoothChildTiming=On(t.smoothChildTiming),ke.remove(n),n._dp=0,n._time=n._tTime=ke._time,i=ke._first;i;)r=i._next,(e||!(!i._dur&&i instanceof Xe&&i.vars.onComplete===i._targets[0]))&&Ii(n,i,i._start-i._delay),i=r;return Ii(ke,n,0),n},context:function(t,e){return t?new Yp(t,e):Ne},matchMedia:function(t){return new lv(t)},matchMediaRefresh:function(){return Ys.forEach(function(t){var e=t.conditions,n,i;for(i in e)e[i]&&(e[i]=!1,n=1);n&&t.revert()})||na()},addEventListener:function(t,e){var n=el[t]||(el[t]=[]);~n.indexOf(e)||n.push(e)},removeEventListener:function(t,e){var n=el[t],i=n&&n.indexOf(e);i>=0&&n.splice(i,1)},utils:{wrap:k0,wrapYoyo:z0,distribute:Dp,random:Np,snap:Up,normalize:B0,getUnit:ln,clamp:U0,splitColor:zp,toArray:ci,selector:Mh,mapRange:Fp,pipe:O0,unitize:F0,interpolate:V0,shuffle:Lp},install:Mp,effects:hh,ticker:Nn,updateRoot:fn.updateRoot,plugins:Un,globalTimeline:ke,core:{PropTween:En,globals:Sp,Tween:Xe,Timeline:fn,Animation:ea,getCache:gs,_removeLinkedListItem:ul,reverting:function(){return an},context:function(t){return t&&Ne&&(Ne.data.push(t),t._ctx=Ne),Ne},suppressOverwrites:function(t){return wh=t}}};Tn("to,from,fromTo,delayedCall,set,killTweensOf",function(s){return ll[s]=Xe[s]});Nn.add(fn.updateRoot);Ur=ll.to({},{duration:0});var cv=function(t,e){for(var n=t._pt;n&&n.p!==e&&n.op!==e&&n.fp!==e;)n=n._next;return n},hv=function(t,e){var n=t._targets,i,r,o;for(i in e)for(r=n.length;r--;)o=t._ptLookup[r][i],o&&(o=o.d)&&(o._pt&&(o=cv(o,i)),o&&o.modifier&&o.modifier(e[i],t,n[r],i))},mh=function(t,e){return{name:t,headless:1,rawVars:1,init:function(i,r,o){o._onInit=function(a){var l,c;if(Ke(r)&&(l={},Tn(r,function(h){return l[h]=1}),r=l),e){l={};for(c in r)l[c]=e(r[c]);r=l}hv(a,r)}}}},pn=ll.registerPlugin({name:"attr",init:function(t,e,n,i,r){var o,a,l;this.tween=n;for(o in e)l=t.getAttribute(o)||"",a=this.add(t,"setAttribute",(l||0)+"",e[o],i,r,0,0,o),a.op=o,a.b=l,this._props.push(o)},render:function(t,e){for(var n=e._pt;n;)an?n.set(n.t,n.p,n.b,n):n.r(t,n.d),n=n._next}},{name:"endArray",headless:1,init:function(t,e){for(var n=e.length;n--;)this.add(t,n,t[n]||0,e[n],0,0,0,0,0,1)}},mh("roundProps",Sh),mh("modifiers"),mh("snap",Up))||ll;Xe.version=fn.version=pn.version="3.15.1";yp=1;Th()&&Br();var uv=me.Power0,fv=me.Power1,dv=me.Power2,pv=me.Power3,mv=me.Power4,gv=me.Linear,_v=me.Quad,vv=me.Cubic,xv=me.Quart,yv=me.Quint,Mv=me.Strong,Sv=me.Elastic,bv=me.Back,wv=me.SteppedEase,Tv=me.Bounce,Ev=me.Sine,Av=me.Expo,Cv=me.Circ;var qp,xs,Vr,Zh,js,Rv,Zp,$h,Pv=function(){return typeof window<"u"},Xi={},Qs=180/Math.PI,Hr=Math.PI/180,zr=Math.atan2,$p=1e8,Jh=/([A-Z])/g,Iv=/(left|right|width|margin|padding|x)/i,Lv=/[\s,\(]\S/,Di={autoAlpha:"opacity,visibility",scale:"scaleX,scaleY",alpha:"opacity"},Wh=function(t,e){return e.set(e.t,e.p,Math.round((e.s+e.c*t)*1e4)/1e4+e.u,e)},Dv=function(t,e){return e.set(e.t,e.p,t===1?e.e:Math.round((e.s+e.c*t)*1e4)/1e4+e.u,e)},Uv=function(t,e){return e.set(e.t,e.p,t?Math.round((e.s+e.c*t)*1e4)/1e4+e.u:e.b,e)},Nv=function(t,e){return e.set(e.t,e.p,t===1?e.e:t?Math.round((e.s+e.c*t)*1e4)/1e4+e.u:e.b,e)},Ov=function(t,e){var n=e.s+e.c*t;e.set(e.t,e.p,~~(n+(n<0?-.5:.5))+e.u,e)},im=function(t,e){return e.set(e.t,e.p,t?e.e:e.b,e)},sm=function(t,e){return e.set(e.t,e.p,t!==1?e.b:e.e,e)},Fv=function(t,e,n){return t.style[e]=n},Bv=function(t,e,n){return t.style.setProperty(e,n)},kv=function(t,e,n){return t._gsap[e]=n},zv=function(t,e,n){return t._gsap.scaleX=t._gsap.scaleY=n},Vv=function(t,e,n,i,r){var o=t._gsap;o.scaleX=o.scaleY=n,o.renderTransform(r,o)},Hv=function(t,e,n,i,r){var o=t._gsap;o[e]=n,o.renderTransform(r,o)},ze="transform",Bn=ze+"Origin",Gv=function s(t,e){var n=this,i=this.target,r=i.style,o=i._gsap;if(t in Xi&&r){if(this.tfm=this.tfm||{},t!=="transform")t=Di[t]||t,~t.indexOf(",")?t.split(",").forEach(function(a){return n.tfm[a]=Wi(i,a)}):this.tfm[t]=o.x?o[t]:Wi(i,t),t===Bn&&(this.tfm.zOrigin=o.zOrigin);else return Di.transform.split(",").forEach(function(a){return s.call(n,a,e)});if(this.props.indexOf(ze)>=0)return;o.svg&&(this.svgo=i.getAttribute("data-svg-origin"),this.props.push(Bn,e,"")),t=ze}(r||e)&&this.props.push(t,e,r[t])},rm=function(t){t.translate&&(t.removeProperty("translate"),t.removeProperty("scale"),t.removeProperty("rotate"))},Wv=function(){var t=this.props,e=this.target,n=e.style,i=e._gsap,r,o;for(r=0;r<t.length;r+=3)t[r+1]?t[r+1]===2?e[t[r]](t[r+2]):e[t[r]]=t[r+2]:t[r+2]?n[t[r]]=t[r+2]:n.removeProperty(t[r].substr(0,2)==="--"?t[r]:t[r].replace(Jh,"-$1").toLowerCase());if(this.tfm){for(o in this.tfm)i[o]=this.tfm[o];i.svg&&(i.renderTransform(),e.setAttribute("data-svg-origin",this.svgo||"")),r=$h(),(!r||!r.isStart)&&!n[ze]&&(rm(n),i.zOrigin&&n[Bn]&&(n[Bn]+=" "+i.zOrigin+"px",i.zOrigin=0,i.renderTransform()),i.uncache=1)}},om=function(t,e){var n={target:t,props:[],revert:Wv,save:Gv};return t._gsap||pn.core.getCache(t),e&&t.style&&t.nodeType&&e.split(",").forEach(function(i){return n.save(i)}),n},am,Xh=function(t,e){var n=xs.createElementNS?xs.createElementNS((e||"http://www.w3.org/1999/xhtml").replace(/^https/,"http"),t):xs.createElement(t);return n&&n.style?n:xs.createElement(t)},qn=function s(t,e,n){var i=getComputedStyle(t);return i[e]||i.getPropertyValue(e.replace(Jh,"-$1").toLowerCase())||i.getPropertyValue(e)||!n&&s(t,Gr(e)||e,1)||""},Jp="O,Moz,ms,Ms,Webkit".split(","),Gr=function(t,e,n){var i=e||js,r=i.style,o=5;if(t in r&&!n)return t;for(t=t.charAt(0).toUpperCase()+t.substr(1);o--&&!(Jp[o]+t in r););return o<0?null:(o===3?"ms":o>=0?Jp[o]:"")+t},Yh=function(){Pv()&&window.document&&(qp=window,xs=qp.document,Vr=xs.documentElement,js=Xh("div")||{style:{}},Rv=Xh("div"),ze=Gr(ze),Bn=ze+"Origin",js.style.cssText="border-width:0;line-height:0;position:absolute;padding:0",am=!!Gr("perspective"),$h=pn.core.reverting,Zh=1)},Kp=function(t){var e=t.ownerSVGElement,n=Xh("svg",e&&e.getAttribute("xmlns")||"http://www.w3.org/2000/svg"),i=t.cloneNode(!0),r;i.style.display="block",n.appendChild(i),Vr.appendChild(n);try{r=i.getBBox()}catch{}return n.removeChild(i),Vr.removeChild(n),r},Qp=function(t,e){for(var n=e.length;n--;)if(t.hasAttribute(e[n]))return t.getAttribute(e[n])},lm=function(t){var e,n;try{e=t.getBBox()}catch{e=Kp(t),n=1}return e&&(e.width||e.height)||n||(e=Kp(t)),e&&!e.width&&!e.x&&!e.y?{x:+Qp(t,["x","cx","x1"])||0,y:+Qp(t,["y","cy","y1"])||0,width:0,height:0}:e},cm=function(t){return!!(t.getCTM&&(!t.parentNode||t.ownerSVGElement)&&lm(t))},Ms=function(t,e){if(e){var n=t.style,i;e in Xi&&e!==Bn&&(e=ze),n.removeProperty?(i=e.substr(0,2),(i==="ms"||e.substr(0,6)==="webkit")&&(e="-"+e),n.removeProperty(i==="--"?e:e.replace(Jh,"-$1").toLowerCase())):n.removeAttribute(e)}},ys=function(t,e,n,i,r,o){var a=new En(t._pt,e,n,0,1,o?sm:im);return t._pt=a,a.b=i,a.e=r,t._props.push(n),a},jp={deg:1,rad:1,turn:1},Xv={grid:1,flex:1},Ss=function s(t,e,n,i){var r=parseFloat(n)||0,o=(n+"").trim().substr((r+"").length)||"px",a=js.style,l=Iv.test(e),c=t.tagName.toLowerCase()==="svg",h=(c?"client":"offset")+(l?"Width":"Height"),u=100,f=i==="px",d=i==="%",g,_,m,p;if(i===o||!r||jp[i]||jp[o])return r;if(o!=="px"&&!f&&(r=s(t,e,n,"px")),p=t.getCTM&&cm(t),(d||o==="%")&&(Xi[e]||~e.indexOf("adius")))return g=p?t.getBBox()[l?"width":"height"]:t[h],Ge(d?r/g*u:r/100*g);if(a[l?"width":"height"]=u+(f?o:i),_=i!=="rem"&&~e.indexOf("adius")||i==="em"&&t.appendChild&&!c?t:t.parentNode,p&&(_=(t.ownerSVGElement||{}).parentNode),(!_||_===xs||!_.appendChild)&&(_=xs.body),m=_._gsap,m&&d&&m.width&&l&&m.time===Nn.time&&!m.uncache)return Ge(r/m.width*u);if(d&&(e==="height"||e==="width")){var S=t.style[e];t.style[e]=u+i,g=t[h],S?t.style[e]=S:Ms(t,e)}else(d||o==="%")&&!Xv[qn(_,"display")]&&(a.position=qn(t,"position")),_===t&&(a.position="static"),_.appendChild(js),g=js[h],_.removeChild(js),a.position="absolute";return l&&d&&(m=gs(_),m.time=Nn.time,m.width=_[h]),Ge(f?g*r/u:g&&r?u/g*r:0)},Wi=function(t,e,n,i){var r;return Zh||Yh(),e in Di&&e!=="transform"&&(e=Di[e],~e.indexOf(",")&&(e=e.split(",")[0])),Xi[e]&&e!=="transform"?(r=oa(t,i),r=e!=="transformOrigin"?r[e]:r.svg?r.origin:gl(qn(t,Bn))+" "+r.zOrigin+"px"):(r=t.style[e],(!r||r==="auto"||i||~(r+"").indexOf("calc("))&&(r=ml[e]&&ml[e](t,e,n)||qn(t,e)||Lh(t,e)||(e==="opacity"?1:0))),n&&!~(r+"").trim().indexOf(" ")?Ss(t,e,r,n)+n:r},Yv=function(t,e,n,i){if(!n||n==="none"){var r=Gr(e,t,1),o=r&&qn(t,r,1);o&&o!==n?(e=r,n=o):e==="borderColor"&&(n=qn(t,"borderTopColor"))}var a=new En(this._pt,t.style,e,0,1,zh),l=0,c=0,h,u,f,d,g,_,m,p,S,y,v,E;if(a.b=n,a.e=i,n+="",i+="",i.substring(0,6)==="var(--"&&(i=qn(t,i.substring(4,i.indexOf(")")))),i==="auto"&&(_=t.style[e],t.style[e]=i,i=qn(t,e)||i,_?t.style[e]=_:Ms(t,e)),h=[n,i],Uh(h),n=h[0],i=h[1],f=n.match(qs)||[],E=i.match(qs)||[],E.length){for(;u=qs.exec(i);)m=u[0],S=i.substring(l,u.index),g?g=(g+1)%5:(S.substr(-5)==="rgba("||S.substr(-5)==="hsla(")&&(g=1),m!==(_=f[c++]||"")&&(d=parseFloat(_)||0,v=_.substr((d+"").length),m.charAt(1)==="="&&(m=Zs(d,m)+v),p=parseFloat(m),y=m.substr((p+"").length),l=qs.lastIndex-y.length,y||(y=y||Fn.units[e]||v,l===i.length&&(i+=y,a.e+=y)),v!==y&&(d=Ss(t,e,_,y)||0),a._pt={_next:a._pt,p:S||c===1?S:",",s:d,c:p-d,m:g&&g<4||e==="zIndex"?Math.round:0});a.c=l<i.length?i.substring(l,i.length):""}else a.r=e==="display"&&i==="none"?sm:im;return Ah.test(i)&&(a.e=0),this._pt=a,a},tm={top:"0%",bottom:"100%",left:"0%",right:"100%",center:"50%"},qv=function(t){var e=t.split(" "),n=e[0],i=e[1]||"50%";return(n==="top"||n==="bottom"||i==="left"||i==="right")&&(t=n,n=i,i=t),e[0]=tm[n]||n,e[1]=tm[i]||i,e.join(" ")},Zv=function(t,e){if(e.tween&&e.tween._time===e.tween._dur){var n=e.t,i=n.style,r=e.u,o=n._gsap,a,l,c;if(r==="all"||r===!0)i.cssText="",l=1;else for(r=r.split(","),c=r.length;--c>-1;)a=r[c],Xi[a]&&(l=1,a=a==="transformOrigin"?Bn:ze),Ms(n,a);l&&(Ms(n,ze),o&&(o.svg&&n.removeAttribute("transform"),i.scale=i.rotate=i.translate="none",oa(n,1),o.uncache=1,rm(i)))}},ml={clearProps:function(t,e,n,i,r){if(r.data!=="isFromStart"){var o=t._pt=new En(t._pt,e,n,0,0,Zv);return o.u=i,o.pr=-10,o.tween=r,t._props.push(n),1}}},ra=[1,0,0,1,0,0],hm={},um=function(t){return t==="matrix(1, 0, 0, 1, 0, 0)"||t==="none"||!t},em=function(t){var e=qn(t,ze);return um(e)?ra:e.substr(7).match(Eh).map(Ge)},Kh=function(t,e){var n=t._gsap||gs(t),i=t.style,r=em(t),o,a,l,c;return n.svg&&t.getAttribute("transform")?(l=t.transform.baseVal.consolidate().matrix,r=[l.a,l.b,l.c,l.d,l.e,l.f],r.join(",")==="1,0,0,1,0,0"?ra:r):(r===ra&&!t.offsetParent&&t!==Vr&&!n.svg&&(l=i.display,i.display="block",o=t.parentNode,(!o||!t.offsetParent&&!t.getBoundingClientRect().width)&&(c=1,a=t.nextElementSibling,Vr.appendChild(t)),r=em(t),l?i.display=l:Ms(t,"display"),c&&(a?o.insertBefore(t,a):o?o.appendChild(t):Vr.removeChild(t))),e&&r.length>6?[r[0],r[1],r[4],r[5],r[12],r[13]]:r)},qh=function(t,e,n,i,r,o){var a=t._gsap,l=r||Kh(t,!0),c=a.xOrigin||0,h=a.yOrigin||0,u=a.xOffset||0,f=a.yOffset||0,d=l[0],g=l[1],_=l[2],m=l[3],p=l[4],S=l[5],y=e.split(" "),v=parseFloat(y[0])||0,E=parseFloat(y[1])||0,A,T,R,M;n?l!==ra&&(T=d*m-g*_)&&(R=v*(m/T)+E*(-_/T)+(_*S-m*p)/T,M=v*(-g/T)+E*(d/T)-(d*S-g*p)/T,v=R,E=M):(A=lm(t),v=A.x+(~y[0].indexOf("%")?v/100*A.width:v),E=A.y+(~(y[1]||y[0]).indexOf("%")?E/100*A.height:E)),i||i!==!1&&a.smooth?(p=v-c,S=E-h,a.xOffset=u+(p*d+S*_)-p,a.yOffset=f+(p*g+S*m)-S):a.xOffset=a.yOffset=0,a.xOrigin=v,a.yOrigin=E,a.smooth=!!i,a.origin=e,a.originIsAbsolute=!!n,t.style[Bn]="0px 0px",o&&(ys(o,a,"xOrigin",c,v),ys(o,a,"yOrigin",h,E),ys(o,a,"xOffset",u,a.xOffset),ys(o,a,"yOffset",f,a.yOffset)),t.setAttribute("data-svg-origin",v+" "+E)},oa=function(t,e){var n=t._gsap||new Nh(t);if("x"in n&&!e&&!n.uncache)return n;var i=t.style,r=n.scaleX<0,o="px",a="deg",l=getComputedStyle(t),c=qn(t,Bn)||"0",h,u,f,d,g,_,m,p,S,y,v,E,A,T,R,M,x,L,U,F,z,q,H,W,V,st,I,at,Dt,Vt,Z,rt;return h=u=f=_=m=p=S=y=v=0,d=g=1,n.svg=!!(t.getCTM&&cm(t)),l.translate&&((l.translate!=="none"||l.scale!=="none"||l.rotate!=="none")&&(i[ze]=(l.translate!=="none"?"translate3d("+(l.translate+" 0 0").split(" ").slice(0,3).join(", ")+") ":"")+(l.rotate!=="none"?"rotate("+l.rotate+") ":"")+(l.scale!=="none"?"scale("+l.scale.split(" ").join(",")+") ":"")+(l[ze]!=="none"?l[ze]:"")),i.scale=i.rotate=i.translate="none"),T=Kh(t,n.svg),n.svg&&(n.uncache?(V=t.getBBox(),c=n.xOrigin-V.x+"px "+(n.yOrigin-V.y)+"px",W=""):W=!e&&t.getAttribute("data-svg-origin"),qh(t,W||c,!!W||n.originIsAbsolute,n.smooth!==!1,T)),E=n.xOrigin||0,A=n.yOrigin||0,T!==ra&&(L=T[0],U=T[1],F=T[2],z=T[3],h=q=T[4],u=H=T[5],T.length===6?(d=Math.sqrt(L*L+U*U),g=Math.sqrt(z*z+F*F),_=L||U?zr(U,L)*Qs:0,S=F||z?zr(F,z)*Qs+_:0,S&&(g*=Math.abs(Math.cos(S*Hr))),n.svg&&(h-=E-(E*L+A*F),u-=A-(E*U+A*z))):(rt=T[6],Vt=T[7],I=T[8],at=T[9],Dt=T[10],Z=T[11],h=T[12],u=T[13],f=T[14],R=zr(rt,Dt),m=R*Qs,R&&(M=Math.cos(-R),x=Math.sin(-R),W=q*M+I*x,V=H*M+at*x,st=rt*M+Dt*x,I=q*-x+I*M,at=H*-x+at*M,Dt=rt*-x+Dt*M,Z=Vt*-x+Z*M,q=W,H=V,rt=st),R=zr(-F,Dt),p=R*Qs,R&&(M=Math.cos(-R),x=Math.sin(-R),W=L*M-I*x,V=U*M-at*x,st=F*M-Dt*x,Z=z*x+Z*M,L=W,U=V,F=st),R=zr(U,L),_=R*Qs,R&&(M=Math.cos(R),x=Math.sin(R),W=L*M+U*x,V=q*M+H*x,U=U*M-L*x,H=H*M-q*x,L=W,q=V),m&&Math.abs(m)+Math.abs(_)>359.9&&(m=_=0,p=180-p),d=Ge(Math.sqrt(L*L+U*U+F*F)),g=Ge(Math.sqrt(H*H+rt*rt)),R=zr(q,H),S=Math.abs(R)>2e-4?R*Qs:0,v=Z?1/(Z<0?-Z:Z):0),n.svg&&(W=t.getAttribute("transform"),n.forceCSS=t.setAttribute("transform","")||!um(qn(t,ze)),W&&t.setAttribute("transform",W))),Math.abs(S)>90&&Math.abs(S)<270&&(r?(d*=-1,S+=_<=0?180:-180,_+=_<=0?180:-180):(g*=-1,S+=S<=0?180:-180)),e=e||n.uncache,n.x=h-((n.xPercent=h&&(!e&&n.xPercent||(Math.round(t.offsetWidth/2)===Math.round(-h)?-50:0)))?t.offsetWidth*n.xPercent/100:0)+o,n.y=u-((n.yPercent=u&&(!e&&n.yPercent||(Math.round(t.offsetHeight/2)===Math.round(-u)?-50:0)))?t.offsetHeight*n.yPercent/100:0)+o,n.z=f+o,n.scaleX=Ge(d),n.scaleY=Ge(g),n.rotation=Ge(_)+a,n.rotationX=Ge(m)+a,n.rotationY=Ge(p)+a,n.skewX=S+a,n.skewY=y+a,n.transformPerspective=v+o,(n.zOrigin=parseFloat(c.split(" ")[2])||!e&&n.zOrigin||0)&&(i[Bn]=gl(c)),n.xOffset=n.yOffset=0,n.force3D=Fn.force3D,n.renderTransform=n.svg?Jv:am?fm:$v,n.uncache=0,n},gl=function(t){return(t=t.split(" "))[0]+" "+t[1]},Gh=function(t,e,n){var i=ln(e);return Ge(parseFloat(e)+parseFloat(Ss(t,"x",n+"px",i)))+i},$v=function(t,e){e.z="0px",e.rotationY=e.rotationX="0deg",e.force3D=0,fm(t,e)},Js="0deg",sa="0px",Ks=") ",fm=function(t,e){var n=e||this,i=n.xPercent,r=n.yPercent,o=n.x,a=n.y,l=n.z,c=n.rotation,h=n.rotationY,u=n.rotationX,f=n.skewX,d=n.skewY,g=n.scaleX,_=n.scaleY,m=n.transformPerspective,p=n.force3D,S=n.target,y=n.zOrigin,v="",E=p==="auto"&&t&&t!==1||p===!0;if(y&&(u!==Js||h!==Js)){var A=parseFloat(h)*Hr,T=Math.sin(A),R=Math.cos(A),M;A=parseFloat(u)*Hr,M=Math.cos(A),o=Gh(S,o,T*M*-y),a=Gh(S,a,-Math.sin(A)*-y),l=Gh(S,l,R*M*-y+y)}m!==sa&&(v+="perspective("+m+Ks),(i||r)&&(v+="translate("+i+"%, "+r+"%) "),(E||o!==sa||a!==sa||l!==sa)&&(v+=l!==sa||E?"translate3d("+o+", "+a+", "+l+") ":"translate("+o+", "+a+Ks),c!==Js&&(v+="rotate("+c+Ks),h!==Js&&(v+="rotateY("+h+Ks),u!==Js&&(v+="rotateX("+u+Ks),(f!==Js||d!==Js)&&(v+="skew("+f+", "+d+Ks),(g!==1||_!==1)&&(v+="scale("+g+", "+_+Ks),S.style[ze]=v||"translate(0, 0)"},Jv=function(t,e){var n=e||this,i=n.xPercent,r=n.yPercent,o=n.x,a=n.y,l=n.rotation,c=n.skewX,h=n.skewY,u=n.scaleX,f=n.scaleY,d=n.target,g=n.xOrigin,_=n.yOrigin,m=n.xOffset,p=n.yOffset,S=n.forceCSS,y=parseFloat(o),v=parseFloat(a),E,A,T,R,M;l=parseFloat(l),c=parseFloat(c),h=parseFloat(h),h&&(h=parseFloat(h),c+=h,l+=h),l||c?(l*=Hr,c*=Hr,E=Math.cos(l)*u,A=Math.sin(l)*u,T=Math.sin(l-c)*-f,R=Math.cos(l-c)*f,c&&(h*=Hr,M=Math.tan(c-h),M=Math.sqrt(1+M*M),T*=M,R*=M,h&&(M=Math.tan(h),M=Math.sqrt(1+M*M),E*=M,A*=M)),E=Ge(E),A=Ge(A),T=Ge(T),R=Ge(R)):(E=u,R=f,A=T=0),(y&&!~(o+"").indexOf("px")||v&&!~(a+"").indexOf("px"))&&(y=Ss(d,"x",o,"px"),v=Ss(d,"y",a,"px")),(g||_||m||p)&&(y=Ge(y+g-(g*E+_*T)+m),v=Ge(v+_-(g*A+_*R)+p)),(i||r)&&(M=d.getBBox(),y=Ge(y+i/100*M.width),v=Ge(v+r/100*M.height)),M="matrix("+E+","+A+","+T+","+R+","+y+","+v+")",d.setAttribute("transform",M),S&&(d.style[ze]=M)},Kv=function(t,e,n,i,r){var o=360,a=Ke(r),l=parseFloat(r)*(a&&~r.indexOf("rad")?Qs:1),c=l-i,h=i+c+"deg",u,f;return a&&(u=r.split("_")[1],u==="short"&&(c%=o,c!==c%(o/2)&&(c+=c<0?o:-o)),u==="cw"&&c<0?c=(c+o*$p)%o-~~(c/o)*o:u==="ccw"&&c>0&&(c=(c-o*$p)%o-~~(c/o)*o)),t._pt=f=new En(t._pt,e,n,i,c,Dv),f.e=h,f.u="deg",t._props.push(n),f},nm=function(t,e){for(var n in e)t[n]=e[n];return t},Qv=function(t,e,n){var i=nm({},n._gsap),r="perspective,force3D,transformOrigin,svgOrigin",o=n.style,a,l,c,h,u,f,d,g;i.svg?(c=n.getAttribute("transform"),n.setAttribute("transform",""),o[ze]=e,a=oa(n,1),Ms(n,ze),n.setAttribute("transform",c)):(c=getComputedStyle(n)[ze],o[ze]=e,a=oa(n,1),o[ze]=c);for(l in Xi)c=i[l],h=a[l],c!==h&&r.indexOf(l)<0&&(d=ln(c),g=ln(h),u=d!==g?Ss(n,l,c,g):parseFloat(c),f=parseFloat(h),t._pt=new En(t._pt,a,l,u,f-u,Wh),t._pt.u=g||0,t._props.push(l));nm(a,i)};Tn("padding,margin,Width,Radius",function(s,t){var e="Top",n="Right",i="Bottom",r="Left",o=(t<3?[e,n,i,r]:[e+r,e+n,i+n,i+r]).map(function(a){return t<2?s+a:"border"+a+s});ml[t>1?"border"+s:s]=function(a,l,c,h,u){var f,d;if(arguments.length<4)return f=o.map(function(g){return Wi(a,g,c)}),d=f.join(" "),d.split(f[0]).length===5?f[0]:d;f=(h+"").split(" "),d={},o.forEach(function(g,_){return d[g]=f[_]=f[_]||f[(_-1)/2|0]}),a.init(l,d,u)}});var Qh={name:"css",register:Yh,targetTest:function(t){return t.style&&t.nodeType},init:function(t,e,n,i,r){var o=this._props,a=t.style,l=n.vars.startAt,c,h,u,f,d,g,_,m,p,S,y,v,E,A,T,R,M;Zh||Yh(),this.styles=this.styles||om(t),R=this.styles.props,this.tween=n;for(_ in e)if(_!=="autoRound"&&(h=e[_],!(Un[_]&&Fh(_,e,n,i,t,r)))){if(d=typeof h,g=ml[_],d==="function"&&(h=h.call(n,i,t,r),d=typeof h),d==="string"&&~h.indexOf("random(")&&(h=kr(h)),g)g(this,t,_,h,n)&&(T=1);else if(_.substr(0,2)==="--")c=(getComputedStyle(t).getPropertyValue(_)+"").trim(),h+="",Hi.lastIndex=0,Hi.test(c)||(m=ln(c),p=ln(h),p?m!==p&&(c=Ss(t,_,c,p)+p):m&&(h+=m)),this.add(a,"setProperty",c,h,i,r,0,0,_),o.push(_),R.push(_,0,a[_]);else if(d!=="undefined"){if(l&&_ in l?(c=typeof l[_]=="function"?l[_].call(n,i,t,r):l[_],Ke(c)&&~c.indexOf("random(")&&(c=kr(c)),ln(c+"")||c==="auto"||(c+=Fn.units[_]||ln(Wi(t,_))||""),(c+"").charAt(1)==="="&&(c=Wi(t,_))):c=Wi(t,_),f=parseFloat(c),S=d==="string"&&h.charAt(1)==="="&&h.substr(0,2),S&&(h=h.substr(2)),u=parseFloat(h),_ in Di&&(_==="autoAlpha"&&(f===1&&Wi(t,"visibility")==="hidden"&&u&&(f=0),R.push("visibility",0,a.visibility),ys(this,a,"visibility",f?"inherit":"hidden",u?"inherit":"hidden",!u)),_!=="scale"&&_!=="transform"&&(_=Di[_],~_.indexOf(",")&&(_=_.split(",")[0]))),y=_ in Xi,y){if(this.styles.save(_),M=h,d==="string"&&h.substring(0,6)==="var(--"){if(h=qn(t,h.substring(4,h.indexOf(")"))),h.substring(0,5)==="calc("){var x=t.style.perspective;t.style.perspective=h,h=qn(t,"perspective"),x?t.style.perspective=x:Ms(t,"perspective")}u=parseFloat(h)}if(v||(E=t._gsap,E.renderTransform&&!e.parseTransform||oa(t,e.parseTransform),A=e.smoothOrigin!==!1&&E.smooth,v=this._pt=new En(this._pt,a,ze,0,1,E.renderTransform,E,0,-1),v.dep=1),_==="scale")this._pt=new En(this._pt,E,"scaleY",E.scaleY,(S?Zs(E.scaleY,S+u):u)-E.scaleY||0,Wh),this._pt.u=0,o.push("scaleY",_),_+="X";else if(_==="transformOrigin"){R.push(Bn,0,a[Bn]),h=qv(h),E.svg?qh(t,h,0,A,0,this):(p=parseFloat(h.split(" ")[2])||0,p!==E.zOrigin&&ys(this,E,"zOrigin",E.zOrigin,p),ys(this,a,_,gl(c),gl(h)));continue}else if(_==="svgOrigin"){qh(t,h,1,A,0,this);continue}else if(_ in hm){Kv(this,E,_,f,S?Zs(f,S+h):h);continue}else if(_==="smoothOrigin"){ys(this,E,"smooth",E.smooth,h);continue}else if(_==="force3D"){E[_]=h;continue}else if(_==="transform"){Qv(this,h,t);continue}}else _ in a||(_=Gr(_)||_);if(y||(u||u===0)&&(f||f===0)&&!Lv.test(h)&&_ in a)m=(c+"").substr((f+"").length),u||(u=0),p=ln(h)||(_ in Fn.units?Fn.units[_]:m),m!==p&&(f=Ss(t,_,c,p)),this._pt=new En(this._pt,y?E:a,_,f,(S?Zs(f,S+u):u)-f,!y&&(p==="px"||_==="zIndex")&&e.autoRound!==!1?Ov:Wh),this._pt.u=p||0,y&&M!==h?(this._pt.b=c,this._pt.e=M,this._pt.r=Nv):m!==p&&p!=="%"&&(this._pt.b=c,this._pt.r=Uv);else if(_ in a)Yv.call(this,t,_,c,S?S+h:h);else if(_ in t)this.add(t,_,c||t[_],S?S+h:h,i,r);else if(_!=="parseTransform"){hl(_,h);continue}y||(_ in a?R.push(_,0,a[_]):typeof t[_]=="function"?R.push(_,2,t[_]()):R.push(_,1,c||t[_])),o.push(_)}}T&&Hh(this)},render:function(t,e){if(e.tween._time||!$h())for(var n=e._pt;n;)n.r(t,n.d),n=n._next;else e.styles.revert()},get:Wi,aliases:Di,getSetter:function(t,e,n){var i=Di[e];return i&&i.indexOf(",")<0&&(e=i),e in Xi&&e!==Bn&&(t._gsap.x||Wi(t,"x"))?n&&Zp===n?e==="scale"?zv:kv:(Zp=n||{})&&(e==="scale"?Vv:Hv):t.style&&!cl(t.style[e])?Fv:~e.indexOf("-")?Bv:pl(t,e)},core:{_removeProperty:Ms,_getMatrix:Kh}};pn.utils.checkPrefix=Gr;pn.core.getStyleSaver=om;(function(s,t,e,n){var i=Tn(s+","+t+","+e,function(r){Xi[r]=1});Tn(t,function(r){Fn.units[r]="deg",hm[r]=1}),Di[i[13]]=s+","+t,Tn(n,function(r){var o=r.split(":");Di[o[1]]=i[o[0]]})})("x,y,z,scale,scaleX,scaleY,xPercent,yPercent","rotation,rotationX,rotationY,skewX,skewY","transform,transformOrigin,svgOrigin,force3D,smoothOrigin,transformPerspective","0:translateX,1:translateY,2:translateZ,8:rotate,8:rotationZ,8:rotateZ,9:rotateX,10:rotateY");Tn("x,y,z,top,right,bottom,left,width,height,fontSize,padding,margin,perspective",function(s){Fn.units[s]="px"});pn.registerPlugin(Qh);var Le=pn.registerPlugin(Qh)||pn,hT=Le.core.Tween;function dm(s,t){for(var e=0;e<t.length;e++){var n=t[e];n.enumerable=n.enumerable||!1,n.configurable=!0,"value"in n&&(n.writable=!0),Object.defineProperty(s,n.key,n)}}function jv(s,t,e){return t&&dm(s.prototype,t),e&&dm(s,e),s}var cn,xl,tx,kn,bs,ws,Xr,mm,tr,Yr,gm,Yi,vi,_m,vm=function(){return cn||typeof window<"u"&&(cn=window.gsap)&&cn.registerPlugin&&cn},xm=1,Wr=[],le=[],xi=[],la=Date.now,jh=function(t,e){return e},ex=function(){var t=Yr.core,e=t.bridge||{},n=t._scrollers,i=t._proxies;n.push.apply(n,le),i.push.apply(i,xi),le=n,xi=i,jh=function(o,a){return e[o](a)}},Zi=function(t,e){return~xi.indexOf(t)&&xi[xi.indexOf(t)+1][e]},ca=function(t){return!!~gm.indexOf(t)},Cn=function(t,e,n,i,r){return t.addEventListener(e,n,{passive:i!==!1,capture:!!r})},An=function(t,e,n,i){return t.removeEventListener(e,n,!!i)},_l="scrollLeft",vl="scrollTop",tu=function(){return Yi&&Yi.isPressed||le.cache++},yl=function(t,e){var n=function i(r){if(r||r===0){xm&&kn.history.scrollRestoration!=="manual"&&(kn.history.scrollRestoration="manual");var o=Yi&&Yi.isPressed;r=i.v=Math.round(r)||(Yi&&Yi.iOS?1:0),t(r),i.cacheID=le.cache,o&&jh("ss",r)}else(e||le.cache!==i.cacheID||jh("ref"))&&(i.cacheID=le.cache,i.v=t());return i.v+i.offset};return n.offset=0,t&&n},mn={s:_l,p:"left",p2:"Left",os:"right",os2:"Right",d:"width",d2:"Width",a:"x",sc:yl(function(s){return arguments.length?kn.scrollTo(s,Ze.sc()):kn.pageXOffset||bs[_l]||ws[_l]||Xr[_l]||0})},Ze={s:vl,p:"top",p2:"Top",os:"bottom",os2:"Bottom",d:"height",d2:"Height",a:"y",op:mn,sc:yl(function(s){return arguments.length?kn.scrollTo(mn.sc(),s):kn.pageYOffset||bs[vl]||ws[vl]||Xr[vl]||0})},Rn=function(t,e){return(e&&e._ctx&&e._ctx.selector||cn.utils.toArray)(t)[0]||(typeof t=="string"&&cn.config().nullTargetWarn!==!1?console.warn("Element not found:",t):null)},nx=function(t,e){for(var n=e.length;n--;)if(e[n]===t||e[n].contains(t))return!0;return!1},qi=function(t,e){var n=e.s,i=e.sc;ca(t)&&(t=bs.scrollingElement||ws);var r=le.indexOf(t),o=i===Ze.sc?1:2;!~r&&(r=le.push(t)-1),le[r+o]||Cn(t,"scroll",tu);var a=le[r+o],l=a||(le[r+o]=yl(Zi(t,n),!0)||(ca(t)?i:yl(function(c){return arguments.length?t[n]=c:t[n]})));return l.target=t,a||(l.smooth=cn.getProperty(t,"scrollBehavior")==="smooth"),l},Ml=function(t,e,n){var i=t,r=t,o=la(),a=o,l=e||50,c=Math.max(500,l*3),h=function(g,_){var m=la();_||m-o>l?(r=i,i=g,a=o,o=m):n?i+=g:i=r+(g-r)/(m-a)*(o-a)},u=function(){r=i=n?0:i,a=o=0},f=function(g){var _=a,m=r,p=la();return(g||g===0)&&g!==i&&h(g),o===a||p-a>c?0:(i+(n?m:-m))/((n?p:o)-_)*1e3};return{update:h,reset:u,getVelocity:f}},aa=function(t,e){return e&&!t._gsapAllow&&t.cancelable!==!1&&t.preventDefault(),t.changedTouches?t.changedTouches[0]:t},pm=function(t){var e=Math.max.apply(Math,t),n=Math.min.apply(Math,t);return Math.abs(e)>=Math.abs(n)?e:n},ym=function(){Yr=cn.core.globals().ScrollTrigger,Yr&&Yr.core&&ex()},Mm=function(t){return cn=t||vm(),!xl&&cn&&typeof document<"u"&&document.body&&(kn=window,bs=document,ws=bs.documentElement,Xr=bs.body,gm=[kn,bs,ws,Xr],tx=cn.utils.clamp,_m=cn.core.context||function(){},tr="onpointerenter"in Xr?"pointer":"mouse",mm=We.isTouch=kn.matchMedia&&kn.matchMedia("(hover: none), (pointer: coarse)").matches?1:"ontouchstart"in kn||navigator.maxTouchPoints>0||navigator.msMaxTouchPoints>0?2:0,vi=We.eventTypes=("ontouchstart"in ws?"touchstart,touchmove,touchcancel,touchend":"onpointerdown"in ws?"pointerdown,pointermove,pointercancel,pointerup":"mousedown,mousemove,mouseup,mouseup").split(","),setTimeout(function(){return xm=0},500),xl=1),Yr||ym(),xl};mn.op=Ze;le.cache=0;var We=(function(){function s(e){this.init(e)}var t=s.prototype;return t.init=function(n){xl||Mm(cn)||console.warn("Please gsap.registerPlugin(Observer)"),Yr||ym();var i=n.tolerance,r=n.dragMinimum,o=n.type,a=n.target,l=n.lineHeight,c=n.debounce,h=n.preventDefault,u=n.onStop,f=n.onStopDelay,d=n.ignore,g=n.wheelSpeed,_=n.event,m=n.onDragStart,p=n.onDragEnd,S=n.onDrag,y=n.onPress,v=n.onRelease,E=n.onRight,A=n.onLeft,T=n.onUp,R=n.onDown,M=n.onChangeX,x=n.onChangeY,L=n.onChange,U=n.onToggleX,F=n.onToggleY,z=n.onHover,q=n.onHoverEnd,H=n.onMove,W=n.ignoreCheck,V=n.isNormalizer,st=n.onGestureStart,I=n.onGestureEnd,at=n.onWheel,Dt=n.onEnable,Vt=n.onDisable,Z=n.onClick,rt=n.scrollSpeed,St=n.capture,ot=n.allowClicks,Rt=n.lockAxis,Bt=n.onLockAxis;this.target=a=Rn(a)||ws,this.vars=n,d&&(d=cn.utils.toArray(d)),i=i||1e-9,r=r||0,g=g||1,rt=rt||1,o=o||"wheel,touch,pointer",c=c!==!1,l||(l=parseFloat(kn.getComputedStyle(Xr).lineHeight)||22);var Wt,Xt,et,nt,P,It,lt,O=this,dt=0,zt=0,At=n.passive||!h&&n.passive!==!1,C=qi(a,mn),b=qi(a,Ze),X=C(),Q=b(),it=~o.indexOf("touch")&&!~o.indexOf("pointer")&&vi[0]==="pointerdown",j=ca(a),xt=a.ownerDocument||bs,pt=[0,0,0],bt=[0,0,0],Kt=0,ut=function(){return Kt=la()},gt=function(ht,Tt){return(O.event=ht)&&d&&nx(ht.target,d)||Tt&&it&&ht.pointerType!=="touch"||W&&W(ht,Tt)},qt=function(){O._vx.reset(),O._vy.reset(),Xt.pause(),u&&u(O)},Yt=function(){var ht=O.deltaX=pm(pt),Tt=O.deltaY=pm(bt),ct=Math.abs(ht)>=i,Nt=Math.abs(Tt)>=i;L&&(ct||Nt)&&L(O,ht,Tt,pt,bt),ct&&(E&&O.deltaX>0&&E(O),A&&O.deltaX<0&&A(O),M&&M(O),U&&O.deltaX<0!=dt<0&&U(O),dt=O.deltaX,pt[0]=pt[1]=pt[2]=0),Nt&&(R&&O.deltaY>0&&R(O),T&&O.deltaY<0&&T(O),x&&x(O),F&&O.deltaY<0!=zt<0&&F(O),zt=O.deltaY,bt[0]=bt[1]=bt[2]=0),(nt||et)&&(H&&H(O),et&&(m&&et===1&&m(O),S&&S(O),et=0),nt=!1),It&&!(It=!1)&&Bt&&Bt(O),P&&(at(O),P=!1),Wt=0},Lt=function(ht,Tt,ct){pt[ct]+=ht,bt[ct]+=Tt,O._vx.update(ht),O._vy.update(Tt),c?Wt||(Wt=requestAnimationFrame(Yt)):Yt()},ee=function(ht,Tt){Rt&&!lt&&(O.axis=lt=Math.abs(ht)>Math.abs(Tt)?"x":"y",It=!0),lt!=="y"&&(pt[2]+=ht,O._vx.update(ht,!0)),lt!=="x"&&(bt[2]+=Tt,O._vy.update(Tt,!0)),c?Wt||(Wt=requestAnimationFrame(Yt)):Yt()},Jt=function(ht){if(!gt(ht,1)){ht=aa(ht,h);var Tt=ht.clientX,ct=ht.clientY,Nt=Tt-O.x,Et=ct-O.y,Ht=O.isDragging;O.x=Tt,O.y=ct,(Ht||(Nt||Et)&&(Math.abs(O.startX-Tt)>=r||Math.abs(O.startY-ct)>=r))&&(et||(et=Ht?2:1),Ht||(O.isDragging=!0),ee(Nt,Et))}},Qt=O.onPress=function(J){gt(J,1)||J&&J.button||(O.axis=lt=null,Xt.pause(),O.isPressed=!0,J=aa(J),dt=zt=0,O.startX=O.x=J.clientX,O.startY=O.y=J.clientY,O._vx.reset(),O._vy.reset(),Cn(V?a:xt,vi[1],Jt,At,!0),O.deltaX=O.deltaY=0,y&&y(O))},D=O.onRelease=function(J){if(!gt(J,1)){An(V?a:xt,vi[1],Jt,!0);var ht=!isNaN(O.y-O.startY),Tt=O.isDragging,ct=Tt&&(Math.abs(O.x-O.startX)>3||Math.abs(O.y-O.startY)>3),Nt=aa(J);!ct&&ht&&(O._vx.reset(),O._vy.reset(),h&&ot&&cn.delayedCall(.08,function(){if(la()-Kt>300&&!J.defaultPrevented){if(J.target.click)J.target.click();else if(xt.createEvent){var Et=xt.createEvent("MouseEvents");Et.initMouseEvent("click",!0,!0,kn,1,Nt.screenX,Nt.screenY,Nt.clientX,Nt.clientY,!1,!1,!1,!1,0,null),J.target.dispatchEvent(Et)}}})),O.isDragging=O.isGesturing=O.isPressed=!1,u&&Tt&&!V&&Xt.restart(!0),et&&Yt(),p&&Tt&&p(O),v&&v(O,ct)}},yt=function(ht){return ht.touches&&ht.touches.length>1&&(O.isGesturing=!0)&&st(ht,O.isDragging)},$=function(){return(O.isGesturing=!1)||I(O)},tt=function(ht){if(!gt(ht)){var Tt=C(),ct=b();Lt((Tt-X)*rt,(ct-Q)*rt,1),X=Tt,Q=ct,u&&Xt.restart(!0)}},Mt=function(ht){if(!gt(ht)){ht=aa(ht,h),at&&(P=!0);var Tt=(ht.deltaMode===1?l:ht.deltaMode===2?kn.innerHeight:1)*g;Lt(ht.deltaX*Tt,ht.deltaY*Tt,0),u&&!V&&Xt.restart(!0)}},wt=function(ht){if(!gt(ht)){var Tt=ht.clientX,ct=ht.clientY,Nt=Tt-O.x,Et=ct-O.y;O.x=Tt,O.y=ct,nt=!0,u&&Xt.restart(!0),(Nt||Et)&&ee(Nt,Et)}},K=function(ht){O.event=ht,z(O)},ft=function(ht){O.event=ht,q(O)},Ut=function(ht){return gt(ht)||aa(ht,h)&&Z(O)};Xt=O._dc=cn.delayedCall(f||.25,qt).pause(),O.deltaX=O.deltaY=0,O._vx=Ml(0,50,!0),O._vy=Ml(0,50,!0),O.scrollX=C,O.scrollY=b,O.isDragging=O.isGesturing=O.isPressed=!1,_m(this),O.enable=function(J){return O.isEnabled||(Cn(j?xt:a,"scroll",tu),o.indexOf("scroll")>=0&&Cn(j?xt:a,"scroll",tt,At,St),o.indexOf("wheel")>=0&&Cn(a,"wheel",Mt,At,St),(o.indexOf("touch")>=0&&mm||o.indexOf("pointer")>=0)&&(Cn(a,vi[0],Qt,At,St),Cn(xt,vi[2],D),Cn(xt,vi[3],D),ot&&Cn(a,"click",ut,!0,!0),Z&&Cn(a,"click",Ut),st&&Cn(xt,"gesturestart",yt),I&&Cn(xt,"gestureend",$),z&&Cn(a,tr+"enter",K),q&&Cn(a,tr+"leave",ft),H&&Cn(a,tr+"move",wt)),O.isEnabled=!0,O.isDragging=O.isGesturing=O.isPressed=nt=et=!1,O._vx.reset(),O._vy.reset(),X=C(),Q=b(),J&&J.type&&Qt(J),Dt&&Dt(O)),O},O.disable=function(){O.isEnabled&&(Wr.filter(function(J){return J!==O&&ca(J.target)}).length||An(j?xt:a,"scroll",tu),O.isPressed&&(O._vx.reset(),O._vy.reset(),An(V?a:xt,vi[1],Jt,!0)),An(j?xt:a,"scroll",tt,St),An(a,"wheel",Mt,St),An(a,vi[0],Qt,St),An(xt,vi[2],D),An(xt,vi[3],D),An(a,"click",ut,!0),An(a,"click",Ut),An(xt,"gesturestart",yt),An(xt,"gestureend",$),An(a,tr+"enter",K),An(a,tr+"leave",ft),An(a,tr+"move",wt),O.isEnabled=O.isPressed=O.isDragging=!1,Vt&&Vt(O))},O.kill=O.revert=function(){O.disable();var J=Wr.indexOf(O);J>=0&&Wr.splice(J,1),Yi===O&&(Yi=0)},Wr.push(O),V&&ca(a)&&(Yi=O),O.enable(_)},jv(s,[{key:"velocityX",get:function(){return this._vx.getVelocity()}},{key:"velocityY",get:function(){return this._vy.getVelocity()}}]),s})();We.version="3.15.1";We.create=function(s){return new We(s)};We.register=Mm;We.getAll=function(){return Wr.slice()};We.getById=function(s){return Wr.filter(function(t){return t.vars.id===s})[0]};vm()&&cn.registerPlugin(We);var Ft,Jr,ue,Te,Jn,be,pu,Fl,Sa,ga,ua,Sl,gn,zl,au,In,Sm,bm,Kr,km,eu,zm,Pn,lu,Vm,Hm,Ts,cu,mu,Qr,gu,Es,hu,nu,bl=1,_n=Date.now,iu=_n(),fi=0,fa=0,wm=function(t,e,n){var i=$n(t)&&(t.substr(0,6)==="clamp("||t.indexOf("max")>-1);return n["_"+e+"Clamp"]=i,i?t.substr(6,t.length-7):t},Tm=function(t,e){return e&&(!$n(t)||t.substr(0,6)!=="clamp(")?"clamp("+t+")":t},ix=function s(){return fa&&requestAnimationFrame(s)},Em=function(){return zl=1},Am=function(){return zl=0},Ui=function(t){return t},da=function(t){return Math.round(t*1e5)/1e5||0},Gm=function(){return typeof window<"u"},Wm=function(){return Ft||Gm()&&(Ft=window.gsap)&&Ft.registerPlugin&&Ft},or=function(t){return!!~pu.indexOf(t)},Xm=function(t){return(t==="Height"?gu:ue["inner"+t])||Jn["client"+t]||be["client"+t]},Ym=function(t){return Zi(t,"getBoundingClientRect")||(or(t)?function(){return Ol.width=ue.innerWidth,Ol.height=gu,Ol}:function(){return $i(t)})},sx=function(t,e,n){var i=n.d,r=n.d2,o=n.a;return(o=Zi(t,"getBoundingClientRect"))?function(){return o()[i]}:function(){return(e?Xm(r):t["client"+r])||0}},rx=function(t,e){return!e||~xi.indexOf(t)?Ym(t):function(){return Ol}},Ni=function(t,e){var n=e.s,i=e.d2,r=e.d,o=e.a;return Math.max(0,(n="scroll"+i)&&(o=Zi(t,n))?o()-Ym(t)()[r]:or(t)?(Jn[n]||be[n])-Xm(i):t[n]-t["offset"+i])},wl=function(t,e){for(var n=0;n<Kr.length;n+=3)(!e||~e.indexOf(Kr[n+1]))&&t(Kr[n],Kr[n+1],Kr[n+2])},$n=function(t){return typeof t=="string"},vn=function(t){return typeof t=="function"},pa=function(t){return typeof t=="number"},er=function(t){return typeof t=="object"},ha=function(t,e,n){return t&&t.progress(e?0:1)&&n&&t.pause()},qr=function(t,e,n){if(t.enabled){var i=t._ctx?t._ctx.add(function(){return e(t,n)}):e(t,n);i&&i.totalTime&&(t.callbackAnimation=i)}},Zr=Math.abs,qm="left",Zm="top",_u="right",vu="bottom",ir="width",sr="height",_a="Right",va="Left",xa="Top",ya="Bottom",$e="padding",hi="margin",to="Width",xu="Height",Qe="px",ui=function(t){return ue.getComputedStyle(t.nodeType===Node.DOCUMENT_NODE?t.scrollingElement:t)},ox=function(t){var e=ui(t).position;t.style.position=e==="absolute"||e==="fixed"?e:"relative"},Cm=function(t,e){for(var n in e)n in t||(t[n]=e[n]);return t},$i=function(t,e){var n=e&&ui(t)[au]!=="matrix(1, 0, 0, 1, 0, 0)"&&Ft.to(t,{x:0,y:0,xPercent:0,yPercent:0,rotation:0,rotationX:0,rotationY:0,scale:1,skewX:0,skewY:0}).progress(1),i=t.getBoundingClientRect?t.getBoundingClientRect():t.scrollingElement.getBoundingClientRect();return n&&n.progress(0).kill(),i},Bl=function(t,e){var n=e.d2;return t["offset"+n]||t["client"+n]||0},$m=function(t){var e=[],n=t.labels,i=t.duration(),r;for(r in n)e.push(n[r]/i);return e},ax=function(t){return function(e){return Ft.utils.snap($m(t),e)}},yu=function(t){var e=Ft.utils.snap(t),n=Array.isArray(t)&&t.slice(0).sort(function(i,r){return i-r});return n?function(i,r,o){o===void 0&&(o=.001);var a;if(!r)return e(i);if(r>0){for(i-=o,a=0;a<n.length;a++)if(n[a]>=i)return n[a];return n[a-1]}else for(a=n.length,i+=o;a--;)if(n[a]<=i)return n[a];return n[0]}:function(i,r,o){o===void 0&&(o=.001);var a=e(i);return!r||Math.abs(a-i)<o||a-i<0==r<0?a:e(r<0?i-t:i+t)}},lx=function(t){return function(e,n){return yu($m(t))(e,n.direction)}},Tl=function(t,e,n,i){return n.split(",").forEach(function(r){return t(e,r,i)})},sn=function(t,e,n,i,r){return t.addEventListener(e,n,{passive:!i,capture:!!r})},nn=function(t,e,n,i){return t.removeEventListener(e,n,!!i)},El=function(t,e,n){n=n&&n.wheelHandler,n&&(t(e,"wheel",n),t(e,"touchmove",n))},Rm={startColor:"green",endColor:"red",indent:0,fontSize:"16px",fontWeight:"normal"},Al={toggleActions:"play",anticipatePin:0},kl={top:0,left:0,center:.5,bottom:1,right:1},Ll=function(t,e){if($n(t)){var n=t.indexOf("="),i=~n?+(t.charAt(n-1)+1)*parseFloat(t.substr(n+1)):0;~n&&(t.indexOf("%")>n&&(i*=e/100),t=t.substr(0,n-1)),t=i+(t in kl?kl[t]*e:~t.indexOf("%")?parseFloat(t)*e/100:parseFloat(t)||0)}return t},Cl=function(t,e,n,i,r,o,a,l){var c=r.startColor,h=r.endColor,u=r.fontSize,f=r.indent,d=r.fontWeight,g=Te.createElement("div"),_=or(n)||Zi(n,"pinType")==="fixed",m=t.indexOf("scroller")!==-1,p=_?be:n.tagName==="IFRAME"?n.contentDocument.body:n,S=t.indexOf("start")!==-1,y=S?c:h,v="border-color:"+y+";font-size:"+u+";color:"+y+";font-weight:"+d+";pointer-events:none;white-space:nowrap;font-family:sans-serif,Arial;z-index:1000;padding:4px 8px;border-width:0;border-style:solid;";return v+="position:"+((m||l)&&_?"fixed;":"absolute;"),(m||l||!_)&&(v+=(i===Ze?_u:vu)+":"+(o+parseFloat(f))+"px;"),a&&(v+="box-sizing:border-box;text-align:left;width:"+a.offsetWidth+"px;"),g._isStart=S,g.setAttribute("class","gsap-marker-"+t+(e?" marker-"+e:"")),g.style.cssText=v,g.innerText=e||e===0?t+"-"+e:t,p.children[0]?p.insertBefore(g,p.children[0]):p.appendChild(g),g._offset=g["offset"+i.op.d2],Dl(g,0,i,S),g},Dl=function(t,e,n,i){var r={display:"block"},o=n[i?"os2":"p2"],a=n[i?"p2":"os2"];t._isFlipped=i,r[n.a+"Percent"]=i?-100:0,r[n.a]=i?"1px":0,r["border"+o+to]=1,r["border"+a+to]=0,r[n.p]=e+"px",Ft.set(t,r)},he=[],uu={},ba,Pm=function(){return _n()-fi>34&&(ba||(ba=requestAnimationFrame(Ji)))},$r=function(){(!Pn||!Pn.isPressed||Pn.startX>be.clientWidth)&&(le.cache++,Pn?ba||(ba=requestAnimationFrame(Ji)):Ji(),fi||lr("scrollStart"),fi=_n())},su=function(){Hm=ue.innerWidth,Vm=ue.innerHeight},ma=function(t){le.cache++,(t===!0||!gn&&!zm&&!Te.fullscreenElement&&!Te.webkitFullscreenElement&&(!lu||Hm!==ue.innerWidth||Math.abs(ue.innerHeight-Vm)>ue.innerHeight*.25))&&Fl.restart(!0)},ar={},cx=[],Jm=function s(){return nn(ie,"scrollEnd",s)||nr(!0)},lr=function(t){return ar[t]&&ar[t].map(function(e){return e()})||cx},Zn=[],Km=function(t){for(var e=0;e<Zn.length;e+=5)(!t||Zn[e+4]&&Zn[e+4].query===t)&&(Zn[e].style.cssText=Zn[e+1],Zn[e].getBBox&&Zn[e].setAttribute("transform",Zn[e+2]||""),Zn[e+3].uncache=1)},Qm=function(){le.cache++,le.forEach(function(t){return vn(t)&&(t.rec=t())})},Mu=function(t,e){var n;for(In=0;In<he.length;In++)n=he[In],n&&(!e||n._ctx===e)&&(t?n.kill(1):n.revert(!0,!0));Es=!0,e&&Km(e),e||lr("revert")},jm=function(t,e){le.cache++,(e||!Ln)&&le.forEach(function(n){return vn(n)&&n.cacheID++&&(n.rec=0)}),$n(t)&&(mu=t,ue.history.scrollRestoration!==t&&(ue.history.scrollRestoration=t))},Ln,rr=0,Im,hx=function(){if(Im!==rr){var t=Im=rr;requestAnimationFrame(function(){return t===rr&&nr(!0)})}},tg=function(){be.appendChild(Qr),gu=!Pn&&Qr.offsetHeight||ue.innerHeight,be.removeChild(Qr)},Lm=function(t){return Sa(".gsap-marker-start, .gsap-marker-end, .gsap-marker-scroller-start, .gsap-marker-scroller-end").forEach(function(e){return e.style.display=t?"none":"block"})},nr=function(t,e){if(Jn=Te.documentElement,be=Te.body,pu=[ue,Te,Jn,be],fi&&!t&&!Es){sn(ie,"scrollEnd",Jm);return}tg(),Ln=ie.isRefreshing=!0,Es||Qm();var n=lr("refreshInit");km&&ie.sort(),e||Mu(),le.forEach(function(i){vn(i)&&(i.smooth&&(i.target.style.scrollBehavior="auto"),i(0))}),he.slice(0).forEach(function(i){return i.refresh()}),Es=!1,he.forEach(function(i){if(i._subPinOffset&&i.pin){var r=i.vars.horizontal?"offsetWidth":"offsetHeight",o=i.pin[r];i.revert(!0,1),i.adjustPinSpacing(i.pin[r]-o),i.refresh()}}),hu=1,Lm(!0),he.forEach(function(i){var r=Ni(i.scroller,i._dir),o=i.vars.end==="max"||i._endClamp&&i.end>r,a=i._startClamp&&i.start>=r;(o||a)&&i.setPositions(a?r-1:i.start,o?Math.max(a?r:i.start+1,r):i.end,!0)}),Lm(!1),hu=0,n.forEach(function(i){return i&&i.render&&i.render(-1)}),le.forEach(function(i){vn(i)&&(i.smooth&&requestAnimationFrame(function(){return i.target.style.scrollBehavior="smooth"}),i.rec&&i(i.rec))}),jm(mu,1),Fl.pause(),rr++,Ln=2,Ji(2),he.forEach(function(i){return vn(i.vars.onRefresh)&&i.vars.onRefresh(i)}),Ln=ie.isRefreshing=!1,lr("refresh")},fu=0,Ul=1,Ma,Ji=function(t){if(t===2||!Ln&&!Es){ie.isUpdating=!0,Ma&&Ma.update(0);var e=he.length,n=_n(),i=n-iu>=50,r=e&&he[0].scroll();if(Ul=fu>r?-1:1,Ln||(fu=r),i&&(fi&&!zl&&n-fi>200&&(fi=0,lr("scrollEnd")),ua=iu,iu=n),Ul<0){for(In=e;In-- >0;)he[In]&&he[In].update(0,i);Ul=1}else for(In=0;In<e;In++)he[In]&&he[In].update(0,i);ie.isUpdating=!1}ba=0},du=[qm,Zm,vu,_u,hi+ya,hi+_a,hi+xa,hi+va,"display","flexShrink","float","zIndex","gridColumnStart","gridColumnEnd","gridRowStart","gridRowEnd","gridArea","justifySelf","alignSelf","placeSelf","order"],Nl=du.concat([ir,sr,"boxSizing","max"+to,"max"+xu,"position",hi,$e,$e+xa,$e+_a,$e+ya,$e+va]),ux=function(t,e,n){jr(n);var i=t._gsap;if(i.spacerIsNative)jr(i.spacerState);else if(t._gsap.swappedIn){var r=e.parentNode;r&&(r.insertBefore(t,e),r.removeChild(e))}t._gsap.swappedIn=!1},ru=function(t,e,n,i){if(!t._gsap.swappedIn){for(var r=du.length,o=e.style,a=t.style,l;r--;)l=du[r],o[l]=n[l];o.position=n.position==="absolute"?"absolute":"relative",n.display==="inline"&&(o.display="inline-block"),a[vu]=a[_u]="auto",o.flexBasis=n.flexBasis||"auto",o.overflow="visible",o.boxSizing="border-box",o[ir]=Bl(t,mn)+Qe,o[sr]=Bl(t,Ze)+Qe,o[$e]=a[hi]=a[Zm]=a[qm]="0",jr(i),a[ir]=a["max"+to]=n[ir],a[sr]=a["max"+xu]=n[sr],a[$e]=n[$e],t.parentNode!==e&&(t.parentNode.insertBefore(e,t),e.appendChild(t)),t._gsap.swappedIn=!0}},fx=/([A-Z])/g,jr=function(t){if(t){var e=t.t.style,n=t.length,i=0,r,o;for((t.t._gsap||Ft.core.getCache(t.t)).uncache=1;i<n;i+=2)o=t[i+1],r=t[i],o?e[r]=o:e[r]&&e.removeProperty(r.replace(fx,"-$1").toLowerCase())}},Rl=function(t){for(var e=Nl.length,n=t.style,i=[],r=0;r<e;r++)i.push(Nl[r],n[Nl[r]]);return i.t=t,i},dx=function(t,e,n){for(var i=[],r=t.length,o=n?8:0,a;o<r;o+=2)a=t[o],i.push(a,a in e?e[a]:t[o+1]);return i.t=t.t,i},Ol={left:0,top:0},Dm=function(t,e,n,i,r,o,a,l,c,h,u,f,d,g){vn(t)&&(t=t(l)),$n(t)&&t.substr(0,3)==="max"&&(t=f+(t.charAt(4)==="="?Ll("0"+t.substr(3),n):0));var _=d?d.time():0,m,p,S;if(d&&d.seek(0),isNaN(t)||(t=+t),pa(t))d&&(t=Ft.utils.mapRange(d.scrollTrigger.start,d.scrollTrigger.end,0,f,t)),a&&Dl(a,n,i,!0);else{vn(e)&&(e=e(l));var y=(t||"0").split(" "),v,E,A,T;S=Rn(e,l)||be,v=$i(S)||{},(!v||!v.left&&!v.top)&&ui(S).display==="none"&&(T=S.style.display,S.style.display="block",v=$i(S),T?S.style.display=T:S.style.removeProperty("display")),E=Ll(y[0],v[i.d]),A=Ll(y[1]||"0",n),t=v[i.p]-c[i.p]-h+E+r-A,a&&Dl(a,A,i,n-A<20||a._isStart&&A>20),n-=n-A}if(g&&(l[g]=t||-.001,t<0&&(t=0)),o){var R=t+n,M=o._isStart;m="scroll"+i.d2,Dl(o,R,i,M&&R>20||!M&&(u?Math.max(be[m],Jn[m]):o.parentNode[m])<=R+1),u&&(c=$i(a),u&&(o.style[i.op.p]=c[i.op.p]-i.op.m-o._offset+Qe))}return d&&S&&(m=$i(S),d.seek(f),p=$i(S),d._caScrollDist=m[i.p]-p[i.p],t=t/d._caScrollDist*f),d&&d.seek(_),d?t:Math.round(t)},px=/(webkit|moz|length|cssText|inset)/i,Um=function(t,e,n,i){if(t.parentNode!==e){var r=t.style,o,a;if(e===be){t._stOrig=r.cssText,a=ui(t);for(o in a)!+o&&!px.test(o)&&a[o]&&typeof r[o]=="string"&&o!=="0"&&(r[o]=a[o]);r.top=n,r.left=i}else r.cssText=t._stOrig;Ft.core.getCache(t).uncache=1,e.appendChild(t)}},eg=function(t,e,n){var i=e,r=i;return function(o){var a=Math.round(t());return a!==i&&a!==r&&Math.abs(a-i)>3&&Math.abs(a-r)>3&&(o=a,n&&n()),r=i,i=Math.round(o),i}},Pl=function(t,e,n){var i={};i[e.p]="+="+n,Ft.set(t,i)},Nm=function(t,e){var n=qi(t,e),i="_scroll"+e.p2,r=function o(a,l,c,h,u){var f=o.tween,d=l.onComplete,g={};c=c||n();var _=eg(n,c,function(){f.kill(),o.tween=0});return u=h&&u||0,h=h||a-c,f&&f.kill(),l[i]=a,l.inherit=!1,l.modifiers=g,g[i]=function(){return _(c+h*f.ratio+u*f.ratio*f.ratio)},l.onUpdate=function(){le.cache++,o.tween&&Ji()},l.onComplete=function(){o.tween=0,d&&d.call(f)},f=o.tween=Ft.to(t,l),f};return t[i]=n,n.wheelHandler=function(){return r.tween&&r.tween.kill()&&(r.tween=0)},sn(t,"wheel",n.wheelHandler),ie.isTouch&&sn(t,"touchmove",n.wheelHandler),r},ie=(function(){function s(e,n){Jr||s.register(Ft)||console.warn("Please gsap.registerPlugin(ScrollTrigger)"),cu(this),this.init(e,n)}var t=s.prototype;return t.init=function(n,i){if(this.progress=this.start=0,this.vars&&this.kill(!0,!0),!fa){this.update=this.refresh=this.kill=Ui;return}n=Cm($n(n)||pa(n)||n.nodeType?{trigger:n}:n,Al);var r=n,o=r.onUpdate,a=r.toggleClass,l=r.id,c=r.onToggle,h=r.onRefresh,u=r.scrub,f=r.trigger,d=r.pin,g=r.pinSpacing,_=r.invalidateOnRefresh,m=r.anticipatePin,p=r.onScrubComplete,S=r.onSnapComplete,y=r.once,v=r.snap,E=r.pinReparent,A=r.pinSpacer,T=r.containerAnimation,R=r.fastScrollEnd,M=r.preventOverlaps,x=n.horizontal||n.containerAnimation&&n.horizontal!==!1?mn:Ze,L=!u&&u!==0,U=Rn(n.scroller||ue),F=Ft.core.getCache(U),z=or(U),q=("pinType"in n?n.pinType:Zi(U,"pinType")||z&&"fixed")==="fixed",H=[n.onEnter,n.onLeave,n.onEnterBack,n.onLeaveBack],W=L&&n.toggleActions.split(" "),V="markers"in n?n.markers:Al.markers,st=z?0:parseFloat(ui(U)["border"+x.p2+to])||0,I=this,at=n.onRefreshInit&&function(){return n.onRefreshInit(I)},Dt=sx(U,z,x),Vt=rx(U,z),Z=0,rt=0,St=0,ot=qi(U,x),Rt,Bt,Wt,Xt,et,nt,P,It,lt,O,dt,zt,At,C,b,X,Q,it,j,xt,pt,bt,Kt,ut,gt,qt,Yt,Lt,ee,Jt,Qt,D,yt,$,tt,Mt,wt,K,ft;if(I._startClamp=I._endClamp=!1,I._dir=x,m*=45,I.scroller=U,I.scroll=T?T.time.bind(T):ot,Xt=ot(),Es&&ot.rec==null&&(ot.rec=Xt),I.vars=n,i=i||n.animation,"refreshPriority"in n&&(km=1,n.refreshPriority===-9999&&(Ma=I)),F.tweenScroll=F.tweenScroll||{top:Nm(U,Ze),left:Nm(U,mn)},I.tweenTo=Rt=F.tweenScroll[x.p],I.scrubDuration=function(ct){yt=pa(ct)&&ct,yt?D?D.duration(ct):D=Ft.to(i,{ease:"expo",totalProgress:"+=0",inherit:!1,duration:yt,paused:!0,onComplete:function(){return p&&p(I)}}):(D&&D.progress(1).kill(),D=0)},i&&(i.vars.lazy=!1,i._initted&&!I.isReverted||i.vars.immediateRender!==!1&&n.immediateRender!==!1&&i.duration()&&i.render(0,!0,!0),I.animation=i.pause(),i.scrollTrigger=I,I.scrubDuration(u),Jt=0,l||(l=i.vars.id)),v&&((!er(v)||v.push)&&(v={snapTo:v}),"scrollBehavior"in be.style&&Ft.set(z?[be,Jn]:U,{scrollBehavior:"auto"}),le.forEach(function(ct){return vn(ct)&&ct.target===(z?Te.scrollingElement||Jn:U)&&(ct.smooth=!1)}),Wt=vn(v.snapTo)?v.snapTo:v.snapTo==="labels"?ax(i):v.snapTo==="labelsDirectional"?lx(i):v.directional!==!1?function(ct,Nt){return yu(v.snapTo)(ct,_n()-rt<500?0:Nt.direction)}:Ft.utils.snap(v.snapTo),$=v.duration||{min:.1,max:2},$=er($)?ga($.min,$.max):ga($,$),tt=Ft.delayedCall(v.delay||yt/2||.1,function(){var ct=ot(),Nt=_n()-rt<500,Et=Rt.tween;if((Nt||Math.abs(I.getVelocity())<10)&&!Et&&!zl&&Z!==ct){var Ht=(ct-nt)/C,fe=i&&!L?i.totalProgress():Ht,jt=Nt?0:(fe-Qt)/(_n()-ua)*1e3||0,_e=Ft.utils.clamp(-Ht,1-Ht,Zr(jt/2)*jt/.185),Ue=Ht+(v.inertia===!1?0:_e),de,pe,ae=v,Ye=ae.onStart,Re=ae.onInterrupt,qe=ae.onComplete;if(de=Wt(Ue,I),pa(de)||(de=Ue),pe=Math.max(0,Math.round(nt+de*C)),ct<=P&&ct>=nt&&pe!==ct){if(Et&&!Et._initted&&Et.data<=Zr(pe-ct))return;v.inertia===!1&&(_e=de-Ht),Rt(pe,{duration:$(Zr(Math.max(Zr(Ue-fe),Zr(de-fe))*.185/jt/.05||0)),ease:v.ease||"power3",data:Zr(pe-ct),onInterrupt:function(){return tt.restart(!0)&&Re&&qr(I,Re)},onComplete:function(){I.update(),Z=ot(),i&&!L&&(D?D.resetTo("totalProgress",de,i._tTime/i._tDur):i.progress(de)),Jt=Qt=i&&!L?i.totalProgress():I.progress,S&&S(I),qe&&qr(I,qe)}},ct,_e*C,pe-ct-_e*C),Ye&&qr(I,Ye,Rt.tween)}}else I.isActive&&Z!==ct&&tt.restart(!0)}).pause()),l&&(uu[l]=I),f=I.trigger=Rn(f||d!==!0&&d),ft=f&&f._gsap&&f._gsap.stRevert,ft&&(ft=ft(I)),d=d===!0?f:Rn(d),$n(a)&&(a={targets:f,className:a}),d&&(g===!1||g===hi||(g=!g&&d.parentNode&&d.parentNode.style&&ui(d.parentNode).display==="flex"?!1:$e),I.pin=d,Bt=Ft.core.getCache(d),Bt.spacer?b=Bt.pinState:(A&&(A=Rn(A),A&&!A.nodeType&&(A=A.current||A.nativeElement),Bt.spacerIsNative=!!A,A&&(Bt.spacerState=Rl(A))),Bt.spacer=it=A||Te.createElement("div"),it.classList.add("pin-spacer"),l&&it.classList.add("pin-spacer-"+l),Bt.pinState=b=Rl(d)),n.force3D!==!1&&Ft.set(d,{force3D:!0}),I.spacer=it=Bt.spacer,ee=ui(d),ut=ee[g+x.os2],xt=Ft.getProperty(d),pt=Ft.quickSetter(d,x.a,Qe),ru(d,it,ee),Q=Rl(d)),V){zt=er(V)?Cm(V,Rm):Rm,O=Cl("scroller-start",l,U,x,zt,0),dt=Cl("scroller-end",l,U,x,zt,0,O),j=O["offset"+x.op.d2];var Ut=Rn(Zi(U,"content")||U);It=this.markerStart=Cl("start",l,Ut,x,zt,j,0,T),lt=this.markerEnd=Cl("end",l,Ut,x,zt,j,0,T),T&&(K=Ft.quickSetter([It,lt],x.a,Qe)),!q&&!(xi.length&&Zi(U,"fixedMarkers")===!0)&&(ox(z?be:U),Ft.set([O,dt],{force3D:!0}),qt=Ft.quickSetter(O,x.a,Qe),Lt=Ft.quickSetter(dt,x.a,Qe))}if(T){var J=T.vars.onUpdate,ht=T.vars.onUpdateParams;T.eventCallback("onUpdate",function(){I.update(0,0,1),J&&J.apply(T,ht||[])})}if(I.previous=function(){return he[he.indexOf(I)-1]},I.next=function(){return he[he.indexOf(I)+1]},I.revert=function(ct,Nt){if(!Nt)return I.kill(!0);var Et=ct!==!1||!I.enabled,Ht=gn;Et!==I.isReverted&&(Et&&(Mt=Math.max(ot(),I.scroll.rec||0),St=I.progress,wt=i&&i.progress()),It&&[It,lt,O,dt].forEach(function(fe){return fe.style.display=Et?"none":"block"}),Et&&(gn=I,I.update(Et)),d&&(!E||!I.isActive)&&(Et?ux(d,it,b):ru(d,it,ui(d),gt)),Et||I.update(Et),gn=Ht,I.isReverted=Et)},I.refresh=function(ct,Nt,Et,Ht){if(!((gn||!I.enabled)&&!Nt)){if(d&&ct&&fi){sn(s,"scrollEnd",Jm);return}!Ln&&at&&at(I),gn=I,Rt.tween&&!Et&&(Rt.tween.kill(),Rt.tween=0),D&&D.pause(),_&&i&&(i.revert({kill:!1}).invalidate(),i.getChildren?i.getChildren(!0,!0,!1).forEach(function(Fe){return Fe.vars.immediateRender&&Fe.render(0,!0,!0)}):i.vars.immediateRender&&i.render(0,!0,!0)),I.isReverted||I.revert(!0,!0),I._subPinOffset=!1;var fe=Dt(),jt=Vt(),_e=T?T.duration():Ni(U,x),Ue=C<=.01||!C,de=0,pe=Ht||0,ae=er(Et)?Et.end:n.end,Ye=n.endTrigger||f,Re=er(Et)?Et.start:n.start||(n.start===0||!f?0:d?"0 0":"0 100%"),qe=I.pinnedContainer=n.pinnedContainer&&Rn(n.pinnedContainer,I),w=f&&Math.max(0,he.indexOf(I))||0,N=w,G,Y,k,mt,_t,Ct,Ot,te,ne,kt,re,xe,ye;for(V&&er(Et)&&(xe=Ft.getProperty(O,x.p),ye=Ft.getProperty(dt,x.p));N-- >0;)Ct=he[N],Ct.end||Ct.refresh(0,1)||(gn=I),Ot=Ct.pin,Ot&&(Ot===f||Ot===d||Ot===qe)&&!Ct.isReverted&&(kt||(kt=[]),kt.unshift(Ct),Ct.revert(!0,!0)),Ct!==he[N]&&(w--,N--);for(vn(Re)&&(Re=Re(I)),Re=wm(Re,"start",I),nt=Dm(Re,f,fe,x,ot(),It,O,I,jt,st,q,_e,T,I._startClamp&&"_startClamp")||(d?-.001:0),vn(ae)&&(ae=ae(I)),$n(ae)&&!ae.indexOf("+=")&&(~ae.indexOf(" ")?ae=($n(Re)?Re.split(" ")[0]:"")+ae:(de=Ll(ae.substr(2),fe),ae=$n(Re)?Re:(T?Ft.utils.mapRange(0,T.duration(),T.scrollTrigger.start,T.scrollTrigger.end,nt):nt)+de,Ye=f)),ae=wm(ae,"end",I),P=Math.max(nt,Dm(ae||(Ye?"100% 0":_e),Ye,fe,x,ot()+de,lt,dt,I,jt,st,q,_e,T,I._endClamp&&"_endClamp"))||-.001,de=0,N=w;N--;)Ct=he[N]||{},Ot=Ct.pin,Ot&&Ct.start-Ct._pinPush<=nt&&!T&&Ct.end>0&&(G=Ct.end-(I._startClamp?Math.max(0,Ct.start):Ct.start),(Ot===f&&Ct.start-Ct._pinPush<nt||Ot===qe)&&isNaN(Re)&&(de+=G*(1-Ct.progress)),Ot===d&&(pe+=G));if(nt+=de,P+=de,I._startClamp&&(I._startClamp+=de),I._endClamp&&!Ln&&(I._endClamp=P||-.001,P=Math.min(P,Ni(U,x))),C=P-nt||(nt-=.01)&&.001,Ue&&(St=Ft.utils.clamp(0,1,Ft.utils.normalize(nt,P,Mt))),I._pinPush=pe,It&&de&&(G={},G[x.a]="+="+de,qe&&(G[x.p]="-="+ot()),Ft.set([It,lt],G)),d&&!(hu&&I.end>=Ni(U,x)))G=ui(d),mt=x===Ze,k=ot(),bt=parseFloat(xt(x.a))+pe,!_e&&P>1&&(re=(z?Te.scrollingElement||Jn:U).style,re={style:re,value:re["overflow"+x.a.toUpperCase()]},z&&ui(be)["overflow"+x.a.toUpperCase()]!=="scroll"&&(re.style["overflow"+x.a.toUpperCase()]="scroll")),ru(d,it,G),Q=Rl(d),Y=$i(d,!0),te=q&&qi(U,mt?mn:Ze)(),g?(gt=[g+x.os2,C+pe+Qe],gt.t=it,N=g===$e?Bl(d,x)+C+pe:0,N&&(gt.push(x.d,N+Qe),it.style.flexBasis!=="auto"&&(it.style.flexBasis=N+Qe)),jr(gt),qe&&he.forEach(function(Fe){Fe.pin===qe&&Fe.vars.pinSpacing!==!1&&(Fe._subPinOffset=!0)}),q&&ot(Mt)):(N=Bl(d,x),N&&it.style.flexBasis!=="auto"&&(it.style.flexBasis=N+Qe)),q&&(_t={top:Y.top+(mt?k-nt:te)+Qe,left:Y.left+(mt?te:k-nt)+Qe,boxSizing:"border-box",position:"fixed"},_t[ir]=_t["max"+to]=Math.ceil(Y.width)+Qe,_t[sr]=_t["max"+xu]=Math.ceil(Y.height)+Qe,_t[hi]=_t[hi+xa]=_t[hi+_a]=_t[hi+ya]=_t[hi+va]="0",_t[$e]=G[$e],_t[$e+xa]=G[$e+xa],_t[$e+_a]=G[$e+_a],_t[$e+ya]=G[$e+ya],_t[$e+va]=G[$e+va],X=dx(b,_t,E),Ln&&ot(0)),i?(ne=i._initted,eu(1),i.render(i.duration(),!0,!0),Kt=xt(x.a)-bt+C+pe,Yt=Math.abs(C-Kt)>1,q&&Yt&&X.splice(X.length-2,2),i.render(0,!0,!0),ne||i.invalidate(!0),i.parent||i.totalTime(i.totalTime()),eu(0)):Kt=C,re&&(re.value?re.style["overflow"+x.a.toUpperCase()]=re.value:re.style.removeProperty("overflow-"+x.a));else if(f&&ot()&&!T)for(Y=f.parentNode;Y&&Y!==be;)Y._pinOffset&&(nt-=Y._pinOffset,P-=Y._pinOffset),Y=Y.parentNode;kt&&kt.forEach(function(Fe){return Fe.revert(!1,!0)}),I.start=nt,I.end=P,Xt=et=Ln?Mt:ot(),!T&&!Ln&&!Es&&(Xt<Mt&&ot(Mt),I.scroll.rec=0),I.revert(!1,!0),rt=_n(),tt&&(Z=-1,tt.restart(!0)),gn=0,i&&L&&(i._initted||wt)&&i.progress()!==wt&&i.progress(wt||0,!0).render(i.time(),!0,!0),(Ue||St!==I.progress||T||_||i&&!i._initted)&&(i&&!L&&(i._initted||St||i.vars.immediateRender!==!1)&&i.totalProgress(T&&nt<-.001&&!St?Ft.utils.normalize(nt,P,0):St,!0),I.progress=Ue||(Xt-nt)/C===St?0:St),d&&g&&(it._pinOffset=Math.round(I.progress*Kt)),D&&D.invalidate(),isNaN(xe)||(xe-=Ft.getProperty(O,x.p),ye-=Ft.getProperty(dt,x.p),Pl(O,x,xe),Pl(It,x,xe-(Ht||0)),Pl(dt,x,ye),Pl(lt,x,ye-(Ht||0))),Ue&&!Ln&&I.update(),h&&!Ln&&!At&&(At=!0,h(I),At=!1)}},I.getVelocity=function(){return(ot()-et)/(_n()-ua)*1e3||0},I.endAnimation=function(){ha(I.callbackAnimation),i&&(D?D.progress(1):i.paused()?L||ha(i,I.direction<0,1):ha(i,i.reversed()))},I.labelToScroll=function(ct){return i&&i.labels&&(nt||I.refresh()||nt)+i.labels[ct]/i.duration()*C||0},I.getTrailing=function(ct){var Nt=he.indexOf(I),Et=I.direction>0?he.slice(0,Nt).reverse():he.slice(Nt+1);return($n(ct)?Et.filter(function(Ht){return Ht.vars.preventOverlaps===ct}):Et).filter(function(Ht){return I.direction>0?Ht.end<=nt:Ht.start>=P})},I.update=function(ct,Nt,Et){if(!(T&&!Et&&!ct)){var Ht=Ln===!0?Mt:I.scroll(),fe=ct?0:(Ht-nt)/C,jt=fe<0?0:fe>1?1:fe||0,_e=I.progress,Ue,de,pe,ae,Ye,Re,qe,w;if(Nt&&(et=Xt,Xt=T?ot():Ht,v&&(Qt=Jt,Jt=i&&!L?i.totalProgress():jt)),m&&d&&!gn&&!bl&&fi&&(!jt&&nt<Ht+(Ht-et)/(_n()-ua)*m?jt=1e-4:jt===1&&P>Ht+(Ht-et)/(_n()-ua)*m&&(jt=.9999)),jt!==_e&&I.enabled){if(Ue=I.isActive=!!jt&&jt<1,de=!!_e&&_e<1,Re=Ue!==de,Ye=Re||!!jt!=!!_e,I.direction=jt>_e?1:-1,I.progress=jt,Ye&&!gn&&(pe=jt&&!_e?0:jt===1?1:_e===1?2:3,L&&(ae=!Re&&W[pe+1]!=="none"&&W[pe+1]||W[pe],w=i&&(ae==="complete"||ae==="reset"||ae in i))),M&&(Re||w)&&(w||u||!i)&&(vn(M)?M(I):I.getTrailing(M).forEach(function(k){return k.endAnimation()})),L||(D&&!gn&&!bl?(D._dp._time-D._start!==D._time&&D.render(D._dp._time-D._start),D.resetTo?D.resetTo("totalProgress",jt,i._tTime/i._tDur):(D.vars.totalProgress=jt,D.invalidate().restart())):i&&i.totalProgress(jt,!!(gn&&(rt||ct)))),d){if(ct&&g&&(it.style[g+x.os2]=ut),!q)pt(da(bt+Kt*jt));else if(Ye){if(qe=!ct&&jt>_e&&P+1>Ht&&Ht+1>=Ni(U,x),E)if(!ct&&(Ue||qe)){var N=$i(d,!0),G=Ht-nt;Um(d,be,N.top+(x===Ze?G:0)+Qe,N.left+(x===Ze?0:G)+Qe)}else Um(d,it);jr(Ue||qe?X:Q),Yt&&jt<1&&Ue||pt(bt+(jt===1&&!qe?Kt:0))}}v&&!Rt.tween&&!gn&&!bl&&tt.restart(!0),a&&(Re||y&&jt&&(jt<1||!nu))&&Sa(a.targets).forEach(function(k){return k.classList[Ue||y?"add":"remove"](a.className)}),o&&!L&&!ct&&o(I),Ye&&!gn?(L&&(w&&(ae==="complete"?i.pause().totalProgress(1):ae==="reset"?i.restart(!0).pause():ae==="restart"?i.restart(!0):i[ae]()),o&&o(I)),(Re||!nu)&&(c&&Re&&qr(I,c),H[pe]&&qr(I,H[pe]),y&&(jt===1?I.kill(!1,1):H[pe]=0),Re||(pe=jt===1?1:3,H[pe]&&qr(I,H[pe]))),R&&!Ue&&Math.abs(I.getVelocity())>(pa(R)?R:2500)&&(ha(I.callbackAnimation),D?D.progress(1):ha(i,ae==="reverse"?1:!jt,1))):L&&o&&!gn&&o(I)}if(Lt){var Y=T?Ht/T.duration()*(T._caScrollDist||0):Ht;qt(Y+(O._isFlipped?1:0)),Lt(Y)}K&&K(-Ht/T.duration()*(T._caScrollDist||0))}},I.enable=function(ct,Nt){I.enabled||(I.enabled=!0,sn(U,"resize",ma),z||sn(U,"scroll",$r),at&&sn(s,"refreshInit",at),ct!==!1&&(I.progress=St=0,Xt=et=Z=ot()),Nt!==!1&&I.refresh())},I.getTween=function(ct){return ct&&Rt?Rt.tween:D},I.setPositions=function(ct,Nt,Et,Ht){if(T){var fe=T.scrollTrigger,jt=T.duration(),_e=fe.end-fe.start;ct=fe.start+_e*ct/jt,Nt=fe.start+_e*Nt/jt}I.refresh(!1,!1,{start:Tm(ct,Et&&!!I._startClamp),end:Tm(Nt,Et&&!!I._endClamp)},Ht),I.update()},I.adjustPinSpacing=function(ct){if(gt&&ct){var Nt=gt.indexOf(x.d)+1;gt[Nt]=parseFloat(gt[Nt])+ct+Qe,gt[1]=parseFloat(gt[1])+ct+Qe,jr(gt)}},I.disable=function(ct,Nt){if(ct!==!1&&I.revert(!0,!0),I.enabled&&(I.enabled=I.isActive=!1,Nt||D&&D.pause(),Mt=0,Bt&&(Bt.uncache=1),at&&nn(s,"refreshInit",at),tt&&(tt.pause(),Rt.tween&&Rt.tween.kill()&&(Rt.tween=0)),!z)){for(var Et=he.length;Et--;)if(he[Et].scroller===U&&he[Et]!==I)return;nn(U,"resize",ma),z||nn(U,"scroll",$r)}},I.kill=function(ct,Nt){I.disable(ct,Nt),D&&!Nt&&D.kill(),l&&delete uu[l];var Et=he.indexOf(I);Et>=0&&he.splice(Et,1),Et===In&&Ul>0&&In--,Et=0,he.forEach(function(Ht){return Ht.scroller===I.scroller&&(Et=1)}),Et||Ln||Es||(I.scroll.rec=0),i&&(i.scrollTrigger=null,ct&&i.revert({kill:!1}),Nt||i.kill()),It&&[It,lt,O,dt].forEach(function(Ht){return Ht.parentNode&&Ht.parentNode.removeChild(Ht)}),Ma===I&&(Ma=0),d&&(Bt&&(Bt.uncache=1),Et=0,he.forEach(function(Ht){return Ht.pin===d&&Et++}),Et||(Bt.spacer=0)),n.onKill&&n.onKill(I)},he.push(I),I.enable(!1,!1),ft&&ft(I),i&&i.add&&!C){var Tt=I.update;I.update=function(){I.update=Tt,le.cache++,nt||P||I.refresh()},Ft.delayedCall(.01,I.update),C=.01,nt=P=0}else I.refresh();d&&hx()},s.register=function(n){return Jr||(Ft=n||Wm(),Gm()&&window.document&&s.enable(),Jr=fa),Jr},s.defaults=function(n){if(n)for(var i in n)Al[i]=n[i];return Al},s.disable=function(n,i){fa=0,he.forEach(function(o){return o[i?"kill":"disable"](n)}),nn(ue,"wheel",$r),nn(Te,"scroll",$r),clearInterval(Sl),nn(Te,"touchcancel",Ui),nn(be,"touchstart",Ui),Tl(nn,Te,"pointerdown,touchstart,mousedown",Em),Tl(nn,Te,"pointerup,touchend,mouseup",Am),Fl.kill(),wl(nn);for(var r=0;r<le.length;r+=3)El(nn,le[r],le[r+1]),El(nn,le[r],le[r+2])},s.enable=function(){if(ue=window,Te=document,Jn=Te.documentElement,be=Te.body,Ft){if(Sa=Ft.utils.toArray,ga=Ft.utils.clamp,cu=Ft.core.context||Ui,eu=Ft.core.suppressOverwrites||Ui,mu=ue.history.scrollRestoration||"auto",fu=ue.pageYOffset||0,Ft.core.globals("ScrollTrigger",s),be){fa=1,Qr=document.createElement("div"),Qr.style.height="100vh",Qr.style.position="absolute",tg(),ix(),We.register(Ft),s.isTouch=We.isTouch,Ts=We.isTouch&&/(iPad|iPhone|iPod|Mac)/g.test(navigator.userAgent),lu=We.isTouch===1,sn(ue,"wheel",$r),pu=[ue,Te,Jn,be],Ft.matchMedia?(s.matchMedia=function(h){var u=Ft.matchMedia(),f;for(f in h)u.add(f,h[f]);return u},Ft.addEventListener("matchMediaInit",function(){Qm(),Mu()}),Ft.addEventListener("matchMediaRevert",function(){return Km()}),Ft.addEventListener("matchMedia",function(){nr(0,1),lr("matchMedia")}),Ft.matchMedia().add("(orientation: portrait)",function(){return su(),su})):console.warn("Requires GSAP 3.11.0 or later"),su(),sn(Te,"scroll",$r);var n=be.hasAttribute("style"),i=be.style,r=i.borderTopStyle,o=Ft.core.Animation.prototype,a,l;for(o.revert||Object.defineProperty(o,"revert",{value:function(){return this.time(-.01,!0)}}),i.borderTopStyle="solid",a=$i(be),Ze.m=Math.round(a.top+Ze.sc())||0,mn.m=Math.round(a.left+mn.sc())||0,r?i.borderTopStyle=r:i.removeProperty("border-top-style"),n||(be.setAttribute("style",""),be.removeAttribute("style")),Sl=setInterval(Pm,250),Ft.delayedCall(.5,function(){return bl=0}),sn(Te,"touchcancel",Ui),sn(be,"touchstart",Ui),Tl(sn,Te,"pointerdown,touchstart,mousedown",Em),Tl(sn,Te,"pointerup,touchend,mouseup",Am),au=Ft.utils.checkPrefix("transform"),Nl.push(au),Jr=_n(),Fl=Ft.delayedCall(.2,nr).pause(),Kr=[Te,"visibilitychange",function(){var h=ue.innerWidth,u=ue.innerHeight;Te.hidden?(Sm=h,bm=u):(Sm!==h||bm!==u)&&ma()},Te,"DOMContentLoaded",nr,ue,"load",nr,ue,"resize",ma],wl(sn),he.forEach(function(h){return h.enable(0,1)}),l=0;l<le.length;l+=3)El(nn,le[l],le[l+1]),El(nn,le[l],le[l+2])}else if(Te){var c=function h(){s.enable(),Te.removeEventListener("DOMContentLoaded",h)};Te.addEventListener("DOMContentLoaded",c)}}},s.config=function(n){"limitCallbacks"in n&&(nu=!!n.limitCallbacks);var i=n.syncInterval;i&&clearInterval(Sl)||(Sl=i)&&setInterval(Pm,i),"ignoreMobileResize"in n&&(lu=s.isTouch===1&&n.ignoreMobileResize),"autoRefreshEvents"in n&&(wl(nn)||wl(sn,n.autoRefreshEvents||"none"),zm=(n.autoRefreshEvents+"").indexOf("resize")===-1)},s.scrollerProxy=function(n,i){var r=Rn(n),o=le.indexOf(r),a=or(r);~o&&le.splice(o,a?6:2),i&&(a?xi.unshift(ue,i,be,i,Jn,i):xi.unshift(r,i))},s.clearMatchMedia=function(n){he.forEach(function(i){return i._ctx&&i._ctx.query===n&&i._ctx.kill(!0,!0)})},s.isInViewport=function(n,i,r){var o=($n(n)?Rn(n):n).getBoundingClientRect(),a=o[r?ir:sr]*i||0;return r?o.right-a>0&&o.left+a<ue.innerWidth:o.bottom-a>0&&o.top+a<ue.innerHeight},s.positionInViewport=function(n,i,r){$n(n)&&(n=Rn(n));var o=n.getBoundingClientRect(),a=o[r?ir:sr],l=i==null?a/2:i in kl?kl[i]*a:~i.indexOf("%")?parseFloat(i)*a/100:parseFloat(i)||0;return r?(o.left+l)/ue.innerWidth:(o.top+l)/ue.innerHeight},s.killAll=function(n){if(he.slice(0).forEach(function(r){return r.vars.id!=="ScrollSmoother"&&r.kill()}),n!==!0){var i=ar.killAll||[];ar={},i.forEach(function(r){return r()})}},s})();ie.version="3.15.1";ie.saveStyles=function(s){return s?Sa(s).forEach(function(t){if(t&&t.style){var e=Zn.indexOf(t);e>=0&&Zn.splice(e,5),Zn.push(t,t.style.cssText,t.getBBox&&t.getAttribute("transform"),Ft.core.getCache(t),cu())}}):Zn};ie.revert=function(s,t){return Mu(!s,t)};ie.create=function(s,t){return new ie(s,t)};ie.refresh=function(s){return s?ma(!0):(Jr||ie.register())&&nr(!0)};ie.update=function(s){return++le.cache&&Ji(s===!0?2:0)};ie.clearScrollMemory=jm;ie.maxScroll=function(s,t){return Ni(s,t?mn:Ze)};ie.getScrollFunc=function(s,t){return qi(Rn(s),t?mn:Ze)};ie.getById=function(s){return uu[s]};ie.getAll=function(){return he.filter(function(s){return s.vars.id!=="ScrollSmoother"})};ie.isScrolling=function(){return!!fi};ie.snapDirectional=yu;ie.addEventListener=function(s,t){var e=ar[s]||(ar[s]=[]);~e.indexOf(t)||e.push(t)};ie.removeEventListener=function(s,t){var e=ar[s],n=e&&e.indexOf(t);n>=0&&e.splice(n,1)};ie.batch=function(s,t){var e=[],n={},i=t.interval||.016,r=t.batchMax||1e9,o=function(c,h){var u=[],f=[],d=Ft.delayedCall(i,function(){h(u,f),u=[],f=[]}).pause();return function(g){u.length||d.restart(!0),u.push(g.trigger),f.push(g),r<=u.length&&d.progress(1)}},a;for(a in t)n[a]=a.substr(0,2)==="on"&&vn(t[a])&&a!=="onRefreshInit"?o(a,t[a]):t[a];return vn(r)&&(r=r(),sn(ie,"refresh",function(){return r=t.batchMax()})),Sa(s).forEach(function(l){var c={};for(a in n)c[a]=n[a];c.trigger=l,e.push(ie.create(c))}),e};var Om=function(t,e,n,i){return e>i?t(i):e<0&&t(0),n>i?(i-e)/(n-e):n<0?e/(e-n):1},ou=function s(t,e){e===!0?t.style.removeProperty("touch-action"):t.style.touchAction=e===!0?"auto":e?"pan-"+e+(We.isTouch?" pinch-zoom":""):"none",t===Jn&&s(be,e)},Il={auto:1,scroll:1},mx=function(t){var e=t.event,n=t.target,i=t.axis,r=(e.changedTouches?e.changedTouches[0]:e).target,o=r._gsap||Ft.core.getCache(r),a=_n(),l;if(!o._isScrollT||a-o._isScrollT>2e3){for(;r&&r!==be&&(r.scrollHeight<=r.clientHeight&&r.scrollWidth<=r.clientWidth||!(Il[(l=ui(r)).overflowY]||Il[l.overflowX]));)r=r.parentNode;o._isScroll=r&&r!==n&&!or(r)&&(Il[(l=ui(r)).overflowY]||Il[l.overflowX]),o._isScrollT=a}(o._isScroll||i==="x")&&(e.stopPropagation(),e._gsapAllow=!0)},ng=function(t,e,n,i){return We.create({target:t,capture:!0,debounce:!1,lockAxis:!0,type:e,onWheel:i=i&&mx,onPress:i,onDrag:i,onScroll:i,onEnable:function(){return n&&sn(Te,We.eventTypes[0],Bm,!1,!0)},onDisable:function(){return nn(Te,We.eventTypes[0],Bm,!0)}})},gx=/(input|label|select|textarea)/i,Fm,Bm=function(t){var e=gx.test(t.target.tagName);(e||Fm)&&(t._gsapAllow=!0,Fm=e)},_x=function(t){er(t)||(t={}),t.preventDefault=t.isNormalizer=t.allowClicks=!0,t.type||(t.type="wheel,touch"),t.debounce=!!t.debounce,t.id=t.id||"normalizer";var e=t,n=e.normalizeScrollX,i=e.momentum,r=e.allowNestedScroll,o=e.onRelease,a,l,c=Rn(t.target)||Jn,h=Ft.core.globals().ScrollSmoother,u=h&&h.get(),f=Ts&&(t.content&&Rn(t.content)||u&&t.content!==!1&&!u.smooth()&&u.content()),d=qi(c,Ze),g=qi(c,mn),_=1,m=(We.isTouch&&ue.visualViewport?ue.visualViewport.scale*ue.visualViewport.width:ue.outerWidth)/ue.innerWidth,p=0,S=vn(i)?function(){return i(a)}:function(){return i||2.8},y,v,E=ng(c,t.type,!0,r),A=function(){return v=!1},T=Ui,R=Ui,M=function(){l=Ni(c,Ze),R=ga(Ts?1:0,l),n&&(T=ga(0,Ni(c,mn))),y=rr},x=function(){f._gsap.y=da(parseFloat(f._gsap.y)+d.offset)+"px",f.style.transform="matrix3d(1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, "+parseFloat(f._gsap.y)+", 0, 1)",d.offset=d.cacheID=0},L=function(){if(v){requestAnimationFrame(A);var V=da(a.deltaY/2),st=R(d.v-V);if(f&&st!==d.v+d.offset){d.offset=st-d.v;var I=da((parseFloat(f&&f._gsap.y)||0)-d.offset);f.style.transform="matrix3d(1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, "+I+", 0, 1)",f._gsap.y=I+"px",d.cacheID=le.cache,Ji()}return!0}d.offset&&x(),v=!0},U,F,z,q,H=function(){M(),U.isActive()&&U.vars.scrollY>l&&(d()>l?U.progress(1)&&d(l):U.resetTo("scrollY",l))};return f&&Ft.set(f,{y:"+=0"}),t.ignoreCheck=function(W){return Ts&&W.type==="touchmove"&&L(W)||_>1.05&&W.type!=="touchstart"||a.isGesturing||W.touches&&W.touches.length>1},t.onPress=function(){v=!1;var W=_;_=da((ue.visualViewport&&ue.visualViewport.scale||1)/m),U.pause(),W!==_&&ou(c,_>1.01?!0:n?!1:"x"),F=g(),z=d(),M(),y=rr},t.onRelease=t.onGestureStart=function(W,V){if(d.offset&&x(),!V)q.restart(!0);else{le.cache++;var st=S(),I,at;n&&(I=g(),at=I+st*.05*-W.velocityX/.227,st*=Om(g,I,at,Ni(c,mn)),U.vars.scrollX=T(at)),I=d(),at=I+st*.05*-W.velocityY/.227,st*=Om(d,I,at,Ni(c,Ze)),U.vars.scrollY=R(at),U.invalidate().duration(st).play(.01),(Ts&&U.vars.scrollY>=l||I>=l-1)&&Ft.to({},{onUpdate:H,duration:st})}o&&o(W)},t.onWheel=function(){U._ts&&U.pause(),_n()-p>1e3&&(y=0,p=_n())},t.onChange=function(W,V,st,I,at){if(rr!==y&&M(),V&&n&&g(T(I[2]===V?F+(W.startX-W.x):g()+V-I[1])),st){d.offset&&x();var Dt=at[2]===st,Vt=Dt?z+W.startY-W.y:d()+st-at[1],Z=R(Vt);Dt&&Vt!==Z&&(z+=Z-Vt),d(Z)}(st||V)&&Ji()},t.onEnable=function(){ou(c,n?!1:"x"),ie.addEventListener("refresh",H),sn(ue,"resize",H),d.smooth&&(d.target.style.scrollBehavior="auto",d.smooth=g.smooth=!1),E.enable()},t.onDisable=function(){ou(c,!0),nn(ue,"resize",H),ie.removeEventListener("refresh",H),E.kill()},t.lockAxis=t.lockAxis!==!1,a=new We(t),a.iOS=Ts,Ts&&!d()&&d(1),Ts&&Ft.ticker.add(Ui),q=a._dc,U=Ft.to(a,{ease:"power4",paused:!0,inherit:!1,scrollX:n?"+=0.1":"+=0",scrollY:"+=0.1",modifiers:{scrollY:eg(d,d(),function(){return U.pause()})},onUpdate:Ji,onComplete:q.vars.onComplete}),a};ie.sort=function(s){if(vn(s))return he.sort(s);var t=ue.pageYOffset||0;return ie.getAll().forEach(function(e){return e._sortY=e.trigger?t+e.trigger.getBoundingClientRect().top:e.start+ue.innerHeight}),he.sort(s||function(e,n){return(e.vars.refreshPriority||0)*-1e6+(e.vars.containerAnimation?1e6:e._sortY)-((n.vars.containerAnimation?1e6:n._sortY)+(n.vars.refreshPriority||0)*-1e6)})};ie.observe=function(s){return new We(s)};ie.normalizeScroll=function(s){if(typeof s>"u")return Pn;if(s===!0&&Pn)return Pn.enable();if(s===!1){Pn&&Pn.kill(),Pn=s;return}var t=s instanceof We?s:_x(s);return Pn&&Pn.target===t.target&&Pn.kill(),or(t.target)&&(Pn=t),t};ie.core={_getVelocityProp:Ml,_inputObserver:ng,_scrollers:le,_proxies:xi,bridge:{ss:function(){fi||lr("scrollStart"),fi=_n()},ref:function(){return gn}}};Wm()&&Ft.registerPlugin(ie);var wa,Ta,ig=typeof Symbol=="function"?Symbol():"_split",bu,vx=()=>bu||Gl.register(window.gsap),sg=typeof Intl<"u"&&"Segmenter"in Intl?new Intl.Segmenter:0,Ea=s=>s?typeof s=="string"?Ea(document.querySelectorAll(s)):"length"in s?Array.from(s).reduce((t,e)=>(typeof e=="string"?t.push(...Ea(e)):t.push(e),t),[]):[s]:[],rg=s=>Ea(s).filter(t=>t&&t.nodeType===1),Vl=[],Su=function(){},xx={add:s=>s()},yx=/\s+/g,og=new RegExp("\\p{RI}\\p{RI}|\\p{Emoji}(\\p{EMod}|\\u{FE0F}\\u{20E3}?|[\\u{E0020}-\\u{E007E}]+\\u{E007F})?(\\u{200D}\\p{Emoji}(\\p{EMod}|\\u{FE0F}\\u{20E3}?|[\\u{E0020}-\\u{E007E}]+\\u{E007F})?)*|.","gu"),Hl={left:0,top:0,width:0,height:0},Mx=(s,t)=>{for(;++t<s.length&&s[t]===Hl;);return s[t]||Hl},ag=({element:s,html:t,ariaL:e,ariaH:n})=>{s.innerHTML=t,e?s.setAttribute("aria-label",e):s.removeAttribute("aria-label"),n?s.setAttribute("aria-hidden",n):s.removeAttribute("aria-hidden")},lg=(s,t)=>{if(t){let e=new Set(s.join("").match(t)||Vl),n=s.length,i,r,o,a;if(e.size)for(;--n>-1;){r=s[n];for(o of e)if(o.startsWith(r)&&o.length>r.length){for(i=0,a=r;o.startsWith(a+=s[n+ ++i])&&a.length<o.length;);if(i&&a.length===o.length){s[n]=o,s.splice(n+1,i);break}}}}return s},cg=s=>window.getComputedStyle(s).display==="inline"&&(s.style.display="inline-block"),eo=(s,t,e)=>t.insertBefore(typeof s=="string"?document.createTextNode(s):s,e),wu=(s,t,e)=>{let n=t[s+"sClass"]||"",{tag:i="div",aria:r="auto",propIndex:o=!1}=t,a=s==="line"?"block":"inline-block",l=n.indexOf("++")>-1,c=h=>{let u=document.createElement(i),f=e.length+1;return n&&(u.className=n+(l?" "+n+f:"")),o&&u.style.setProperty("--"+s,f+""),r!=="none"&&u.setAttribute("aria-hidden","true"),i!=="span"&&(u.style.position="relative",u.style.display=a),u.textContent=h,e.push(u),u};return l&&(n=n.replace("++","")),c.collection=e,c},Sx=(s,t,e,n)=>{let i=wu("line",e,n),r=window.getComputedStyle(s).textAlign||"left";return(o,a)=>{let l=i("");for(l.style.textAlign=r,s.insertBefore(l,t[o]);o<a;o++)l.appendChild(t[o]);l.normalize()}},hg=(s,t,e,n,i,r,o,a,l,c)=>{var h;let u=Array.from(s.childNodes),f=0,{wordDelimiter:d,reduceWhiteSpace:g=!0,prepareText:_}=t,m=s.getBoundingClientRect(),p=m,S=!g&&window.getComputedStyle(s).whiteSpace.substring(0,3)==="pre",y=r&&c&&window.getComputedStyle(s).direction==="rtl",v=0,E=e.collection,A,T,R,M,x,L,U,F,z,q,H,W,V,st,I,at,Dt,Vt;for(typeof d=="object"?(R=d.delimiter||d,T=d.replaceWith||""):T=d===""?"":d||" ",A=T!==" ";f<u.length;f++)if(M=u[f],M.nodeType===3){for(I=M.textContent||"",g?I=I.replace(yx," "):S&&(I=I.replace(/\n/g,T+`
`)),_&&(I=_(I,s)),M.textContent=I,x=T||R?I.split(R||T):I.match(a)||Vl,Dt=x[x.length-1],F=A?Dt.slice(-1)===" ":!Dt,Dt||x.pop(),p=m,U=A?x[0].charAt(0)===" ":!x[0],U&&eo(" ",s,M),x[0]||x.shift(),lg(x,l),r&&c||(M.textContent=""),z=1;z<=x.length;z++)if(at=x[z-1],!g&&S&&at.charAt(0)===`
`&&((h=M.previousSibling)==null||h.remove(),eo(document.createElement("br"),s,M),at=at.slice(1)),!g&&at==="")eo(T,s,M);else if(at===" ")s.insertBefore(document.createTextNode(" "),M);else{if(A&&at.charAt(0)===" "&&eo(" ",s,M),v&&z===1&&!U&&E.indexOf(v.parentNode)>-1?(L=E[E.length-1],L.appendChild(document.createTextNode(n?"":at))):(L=e(n?"":at),eo(L,s,M),v&&z===1&&!U&&L.insertBefore(v,L.firstChild)),n){if(H=sg?lg([...sg.segment(at)].map(Z=>Z.segment),l):at.match(a)||Vl,l){let Z=at.match(l);Z&&Z.some(rt=>H.indexOf(rt)<0)&&(H=at.match(a)||Vl)}for(Vt=0;Vt<H.length;Vt++)L.appendChild(H[Vt]===" "?document.createTextNode(" "):n(H[Vt]))}if(r&&c){if(I=M.textContent=I.substring(at.length+1,I.length),q=L.getBoundingClientRect(),q.top>p.top&&(y?q.left>=p.left:q.left<=p.left)){for(W=s.cloneNode(),V=s.childNodes[0];V&&V!==L;)st=V,V=V.nextSibling,W.appendChild(st);s.parentNode.insertBefore(W,s),i&&cg(W)}p=q}(z<x.length||F)&&eo(z>=x.length?" ":A&&at.slice(-1)===" "?" "+T:T,s,M)}s.removeChild(M),v=0}else M.nodeType===1&&(o&&o.indexOf(M)>-1?(E.indexOf(M.previousSibling)>-1&&E[E.length-1].appendChild(M),v=M):(hg(M,t,e,n,i,r,o,a,l,!0),v=0),i&&cg(M))},ug=class fg{constructor(t,e){this.isSplit=!1,vx(),this.elements=rg(t),this.chars=[],this.words=[],this.lines=[],this.masks=[],this.vars=e,this.elements.forEach(r=>{var o;e.overwrite!==!1&&((o=r[ig])==null||o._data.orig.filter(({element:a})=>a===r).forEach(ag)),r[ig]=this}),this._split=()=>this.isSplit&&this.split(this.vars);let n=[],i=()=>{let r=n.length,o;for(;r--;){o=n[r];let a=o.element.offsetWidth;if(a!==o.width){o.width=a,this._split();return}}};this._data={orig:n,obs:typeof ResizeObserver<"u"&&new ResizeObserver(()=>{clearTimeout(this._data.t),this._data.t=setTimeout(i,200)})},Su(this),this.split(e)}split(t){return(this._ctx||xx).add(()=>{this.isSplit&&this.revert(),this.vars=t=t||this.vars||{};let{type:e="chars,words,lines",aria:n="auto",deepSlice:i=!0,smartWrap:r,onSplit:o,autoSplit:a=!1,specialChars:l,mask:c}=this.vars,h=e.indexOf("lines")>-1,u=e.indexOf("chars")>-1,f=e.indexOf("words")>-1,d=u&&!f&&!h,g=l&&("push"in l?new RegExp("(?:"+l.join("|")+")","gu"):l),_=g?new RegExp(g.source+"|"+og.source,"gu"):og,m=!!t.ignore&&rg(t.ignore),{orig:p,animTime:S,obs:y}=this._data,v;(u||f||h)&&(this.elements.forEach((E,A)=>{p[A]={element:E,html:E.innerHTML,ariaL:E.getAttribute("aria-label"),ariaH:E.getAttribute("aria-hidden")},n==="auto"?E.setAttribute("aria-label",(E.textContent||"").trim()):n==="hidden"&&E.setAttribute("aria-hidden","true");let T=[],R=[],M=[],x=u?wu("char",t,T):null,L=wu("word",t,R),U,F,z,q;if(hg(E,t,L,x,d,i&&(h||d),m,_,g,!1),h){let H=Ea(E.childNodes),W=Sx(E,H,t,M),V,st=[],I=0,at=window.getComputedStyle(E).direction==="rtl",Dt=H.map(rt=>rt.nodeType===1?rt.getBoundingClientRect():Hl),Vt=Hl,Z;for(U=0;U<H.length;U++)V=H[U],V.nodeType===1&&(V.nodeName==="BR"?((!U||H[U-1].nodeName!=="BR")&&(st.push(V),W(I,U+1)),I=U+1,Vt=Mx(Dt,U)):(Z=Dt[U],U&&Z.top>Vt.top&&(at?Z.left+Z.width>Vt.left+1:Z.left<Vt.left+Vt.width-1)&&(W(I,U),I=U),Vt=Z));I<U&&W(I,U),st.forEach(rt=>{var St;return(St=rt.parentNode)==null?void 0:St.removeChild(rt)})}if(!f){for(U=0;U<R.length;U++)if(F=R[U],u||!F.nextSibling||F.nextSibling.nodeType!==3)if(r&&!h){for(z=document.createElement("span"),z.style.whiteSpace="nowrap";F.firstChild;)z.appendChild(F.firstChild);F.replaceWith(z)}else F.replaceWith(...F.childNodes);else q=F.nextSibling,q&&q.nodeType===3&&(q.textContent=(F.textContent||"")+(q.textContent||""),F.remove());R.length=0,E.normalize()}this.lines.push(...M),this.words.push(...R),this.chars.push(...T)}),c&&this[c]&&this.masks.push(...this[c].map(E=>{let A=E.cloneNode();return E.replaceWith(A),A.appendChild(E),E.className&&(A.className=E.className.trim().split(" ").map(T=>T+"-mask").join(" ")),A.style.overflow="clip",A.style.verticalAlign="top",A}))),this.isSplit=!0,Ta&&h&&a&&Ta.addEventListener("loadingdone",this._split),(v=o&&o(this))&&v.totalTime&&(this._data.anim=S?v.totalTime(S):v),h&&a&&this.elements.forEach((E,A)=>{p[A].width=E.offsetWidth,y&&y.observe(E)})}),this}kill(){let{obs:t,t:e}=this._data;t&&t.disconnect(),clearTimeout(e),Ta?.removeEventListener("loadingdone",this._split)}revert(){var t,e;if(this.isSplit){let{orig:n,anim:i}=this._data;this.kill(),n.forEach(ag),this.chars.length=this.words.length=this.lines.length=n.length=this.masks.length=0,this.isSplit=!1,i&&(this._data.animTime=i.totalTime(),i.revert()),(e=(t=this.vars).onRevert)==null||e.call(t,this)}return this}static create(t,e){return new fg(t,e)}static register(t){wa=wa||t||window.gsap,wa&&(Ea=wa.utils.toArray,Su=wa.core.context||Su),!bu&&window.innerWidth>0&&(Ta=document.fonts,bu=!0)}};ug.version="3.15.1";var Gl=ug;var dg="1.3.27";function gg(s,t,e){return Math.max(s,Math.min(t,e))}function bx(s,t,e){return(1-e)*s+e*t}function wx(s,t,e,n){return bx(s,t,1-Math.exp(-e*n))}function Tx(s,t){return(s%t+t)%t}var Ex=class{constructor(){Gt(this,"isRunning",!1);Gt(this,"value",0);Gt(this,"from",0);Gt(this,"to",0);Gt(this,"currentTime",0);Gt(this,"lerp");Gt(this,"duration");Gt(this,"easing");Gt(this,"onUpdate")}advance(s){if(!this.isRunning)return;let t=!1;if(this.duration&&this.easing){this.currentTime+=s;let e=gg(0,this.currentTime/this.duration,1);t=e>=1;let n=t?1:this.easing(e);this.value=this.from+(this.to-this.from)*n}else this.lerp?(this.value=wx(this.value,this.to,this.lerp*60,s),Math.round(this.value)===Math.round(this.to)&&(this.value=this.to,t=!0)):(this.value=this.to,t=!0);t&&this.stop(),this.onUpdate?.(this.value,t)}stop(){this.isRunning=!1}fromTo(s,t,{lerp:e,duration:n,easing:i,onStart:r,onUpdate:o}){this.from=this.value=s,this.to=t,this.lerp=e,this.duration=n,this.easing=i,this.currentTime=0,this.isRunning=!0,r?.(),this.onUpdate=o}};function Ax(s,t){let e;return function(...n){clearTimeout(e),e=setTimeout(()=>{e=void 0,s.apply(this,n)},t)}}var Cx=class{constructor(s,t,{autoResize:e=!0,debounce:n=250}={}){Gt(this,"width",0);Gt(this,"height",0);Gt(this,"scrollHeight",0);Gt(this,"scrollWidth",0);Gt(this,"debouncedResize");Gt(this,"wrapperResizeObserver");Gt(this,"contentResizeObserver");Gt(this,"resize",()=>{this.onWrapperResize(),this.onContentResize()});Gt(this,"onWrapperResize",()=>{this.wrapper instanceof Window?(this.width=window.innerWidth,this.height=window.innerHeight):(this.width=this.wrapper.clientWidth,this.height=this.wrapper.clientHeight)});Gt(this,"onContentResize",()=>{this.wrapper instanceof Window?(this.scrollHeight=this.content.scrollHeight,this.scrollWidth=this.content.scrollWidth):(this.scrollHeight=this.wrapper.scrollHeight,this.scrollWidth=this.wrapper.scrollWidth)});this.wrapper=s,this.content=t,e&&(this.debouncedResize=Ax(this.resize,n),this.wrapper instanceof Window?window.addEventListener("resize",this.debouncedResize):(this.wrapperResizeObserver=new ResizeObserver(this.debouncedResize),this.wrapperResizeObserver.observe(this.wrapper)),this.contentResizeObserver=new ResizeObserver(this.debouncedResize),this.contentResizeObserver.observe(this.content)),this.resize()}destroy(){this.wrapperResizeObserver?.disconnect(),this.contentResizeObserver?.disconnect(),this.wrapper===window&&this.debouncedResize&&window.removeEventListener("resize",this.debouncedResize)}get limit(){return{x:this.scrollWidth-this.width,y:this.scrollHeight-this.height}}},_g=class{constructor(){Gt(this,"events",{})}emit(s,...t){let e=this.events[s]||[];for(let n=0,i=e.length;n<i;n++)e[n]?.(...t)}on(s,t){return this.events[s]?this.events[s].push(t):this.events[s]=[t],()=>{this.events[s]=this.events[s]?.filter(e=>t!==e)}}off(s,t){this.events[s]=this.events[s]?.filter(e=>t!==e)}destroy(){this.events={}}},Rx=100/6,As={passive:!1};function pg(s,t){return s===1?Rx:s===2?t:1}var Px=class{constructor(s,t={wheelMultiplier:1,touchMultiplier:1}){Gt(this,"touchStart",{x:0,y:0});Gt(this,"lastDelta",{x:0,y:0});Gt(this,"window",{width:0,height:0});Gt(this,"emitter",new _g);Gt(this,"onTouchStart",s=>{let{clientX:t,clientY:e}=s.targetTouches?s.targetTouches[0]:s;this.touchStart.x=t,this.touchStart.y=e,this.lastDelta={x:0,y:0},this.emitter.emit("scroll",{deltaX:0,deltaY:0,event:s})});Gt(this,"onTouchMove",s=>{let{clientX:t,clientY:e}=s.targetTouches?s.targetTouches[0]:s,n=-(t-this.touchStart.x)*this.options.touchMultiplier,i=-(e-this.touchStart.y)*this.options.touchMultiplier;this.touchStart.x=t,this.touchStart.y=e,this.lastDelta={x:n,y:i},this.emitter.emit("scroll",{deltaX:n,deltaY:i,event:s})});Gt(this,"onTouchEnd",s=>{this.emitter.emit("scroll",{deltaX:this.lastDelta.x,deltaY:this.lastDelta.y,event:s})});Gt(this,"onWheel",s=>{let{deltaX:t,deltaY:e,deltaMode:n}=s,i=pg(n,this.window.width),r=pg(n,this.window.height);t*=i,e*=r,t*=this.options.wheelMultiplier,e*=this.options.wheelMultiplier,this.emitter.emit("scroll",{deltaX:t,deltaY:e,event:s})});Gt(this,"onWindowResize",()=>{this.window={width:window.innerWidth,height:window.innerHeight}});this.element=s,this.options=t,window.addEventListener("resize",this.onWindowResize),this.onWindowResize(),this.element.addEventListener("wheel",this.onWheel,As),this.element.addEventListener("touchstart",this.onTouchStart,As),this.element.addEventListener("touchmove",this.onTouchMove,As),this.element.addEventListener("touchend",this.onTouchEnd,As)}on(s,t){return this.emitter.on(s,t)}destroy(){this.emitter.destroy(),window.removeEventListener("resize",this.onWindowResize),this.element.removeEventListener("wheel",this.onWheel,As),this.element.removeEventListener("touchstart",this.onTouchStart,As),this.element.removeEventListener("touchmove",this.onTouchMove,As),this.element.removeEventListener("touchend",this.onTouchEnd,As)}},mg=s=>Math.min(1,1.001-2**(-10*s)),vg=class{constructor({wrapper:s=window,content:t=document.documentElement,eventsTarget:e=s,smoothWheel:n=!0,syncTouch:i=!1,syncTouchLerp:r=.075,touchInertiaExponent:o=1.7,duration:a,easing:l,lerp:c=.1,infinite:h=!1,orientation:u="vertical",gestureOrientation:f=u==="horizontal"?"both":"vertical",touchMultiplier:d=1,wheelMultiplier:g=1,autoResize:_=!0,prevent:m,virtualScroll:p,overscroll:S=!0,autoRaf:y=!1,anchors:v=!1,autoToggle:E=!1,allowNestedScroll:A=!1,__experimental__naiveDimensions:T=!1,naiveDimensions:R=T,stopInertiaOnNavigate:M=!1,respectReducedMotion:x=!0}={}){Gt(this,"_isScrolling",!1);Gt(this,"_isStopped",!1);Gt(this,"_isLocked",!1);Gt(this,"_preventNextNativeScrollEvent",!1);Gt(this,"_resetVelocityTimeout",null);Gt(this,"_rafId",null);Gt(this,"_isDraggingSelection",!1);Gt(this,"reducedMotionMediaQuery",window.matchMedia("(prefers-reduced-motion: reduce)"));Gt(this,"isTouching");Gt(this,"isIos");Gt(this,"time",0);Gt(this,"userData",{});Gt(this,"lastVelocity",0);Gt(this,"velocity",0);Gt(this,"direction",0);Gt(this,"options");Gt(this,"targetScroll");Gt(this,"animatedScroll");Gt(this,"animate",new Ex);Gt(this,"emitter",new _g);Gt(this,"dimensions");Gt(this,"virtualScroll");Gt(this,"onScrollEnd",s=>{s instanceof CustomEvent||(this.isScrolling==="smooth"||this.isScrolling===!1)&&s.stopPropagation()});Gt(this,"dispatchScrollendEvent",()=>{this.options.wrapper.dispatchEvent(new CustomEvent("scrollend",{bubbles:this.options.wrapper===window,detail:{lenisScrollEnd:!0}}))});Gt(this,"onTransitionEnd",s=>{s.propertyName?.includes("overflow")&&s.target===this.rootElement&&this.checkOverflow()});Gt(this,"onClick",s=>{let t=s.composedPath().filter(n=>n instanceof HTMLAnchorElement&&n.href).map(n=>new URL(n.href)),e=new URL(window.location.href);if(this.options.anchors){let n=t.find(i=>e.host===i.host&&e.pathname===i.pathname&&i.hash);if(n){let i=typeof this.options.anchors=="object"&&this.options.anchors?this.options.anchors:void 0,r=decodeURIComponent(n.hash);this.scrollTo(r,i);return}}if(this.options.stopInertiaOnNavigate&&t.some(n=>e.host===n.host&&e.pathname!==n.pathname)){this.reset();return}});Gt(this,"onPointerDown",s=>{s.button===1&&this.reset()});Gt(this,"onVirtualScroll",s=>{if(typeof this.options.virtualScroll=="function"&&this.options.virtualScroll(s)===!1)return;let{deltaX:t,deltaY:e,event:n}=s;if(this.emitter.emit("virtual-scroll",{deltaX:t,deltaY:e,event:n}),n.ctrlKey||n.lenisStopPropagation)return;let i=n.type.includes("touch"),r=n.type.includes("wheel");if(i&&this.isIos&&(n.type==="touchstart"&&(this._isDraggingSelection=this.isTouchOnSelectionHandle(n)),this._isDraggingSelection)){n.type==="touchend"&&(this._isDraggingSelection=!1);return}this.isTouching=n.type==="touchstart"||n.type==="touchmove";let o=t===0&&e===0;if(this.options.syncTouch&&i&&n.type==="touchstart"&&o&&!this.isStopped&&!this.isLocked){this.reset();return}let a=this.options.gestureOrientation==="vertical"&&e===0||this.options.gestureOrientation==="horizontal"&&t===0;if(o||a)return;let l=n.composedPath();l=l.slice(0,l.indexOf(this.rootElement));let c=this.options.prevent,h=Math.abs(t)>=Math.abs(e)?"horizontal":"vertical";if(l.find(g=>g instanceof HTMLElement&&(typeof c=="function"&&c?.(g)||g.hasAttribute?.("data-lenis-prevent")||h==="vertical"&&g.hasAttribute?.("data-lenis-prevent-vertical")||h==="horizontal"&&g.hasAttribute?.("data-lenis-prevent-horizontal")||i&&g.hasAttribute?.("data-lenis-prevent-touch")||r&&g.hasAttribute?.("data-lenis-prevent-wheel")||this.options.allowNestedScroll&&this.hasNestedScroll(g,{deltaX:t,deltaY:e}))))return;if(this.isStopped||this.isLocked){n.cancelable&&n.preventDefault();return}if(!(this.options.syncTouch&&i||this.options.smoothWheel&&r)){this.isScrolling="native",this.animate.stop(),n.lenisStopPropagation=!0;return}let u=e;this.options.gestureOrientation==="both"?u=Math.abs(e)>Math.abs(t)?e:t:this.options.gestureOrientation==="horizontal"&&(u=t),(!this.options.overscroll||this.options.infinite||this.options.wrapper!==window&&this.limit>0&&(this.animatedScroll>0&&this.animatedScroll<this.limit||this.animatedScroll===0&&e>0||this.animatedScroll===this.limit&&e<0))&&(n.lenisStopPropagation=!0),n.cancelable&&n.preventDefault();let f=i&&this.options.syncTouch,d=i&&n.type==="touchend";d&&(u=Math.sign(u)*Math.abs(this.velocity)**this.options.touchInertiaExponent),this.scrollTo(this.targetScroll+u,{programmatic:!1,...f?{lerp:d?this.options.syncTouchLerp:1}:{lerp:this.options.lerp,duration:this.options.duration,easing:this.options.easing}})});Gt(this,"onNativeScroll",()=>{if(this._resetVelocityTimeout!==null&&(clearTimeout(this._resetVelocityTimeout),this._resetVelocityTimeout=null),this._preventNextNativeScrollEvent){this._preventNextNativeScrollEvent=!1;return}if(this.isScrolling===!1||this.isScrolling==="native"){let s=this.animatedScroll;this.animatedScroll=this.targetScroll=this.actualScroll,this.lastVelocity=this.velocity,this.velocity=this.animatedScroll-s,this.direction=Math.sign(this.animatedScroll-s),this.isStopped||(this.isScrolling="native"),this.emit(),this.velocity!==0&&(this._resetVelocityTimeout=setTimeout(()=>{this.lastVelocity=this.velocity,this.velocity=0,this.isScrolling=!1,this.emit()},400))}});Gt(this,"raf",s=>{let t=s-(this.time||s);this.time=s,this.animate.advance(t*.001),this.options.autoRaf&&(this._rafId=requestAnimationFrame(this.raf))});window.lenisVersion=dg,window.lenis||(window.lenis={}),window.lenis.version=dg,u==="horizontal"&&(window.lenis.horizontal=!0),i===!0&&(window.lenis.touch=!0),this.isIos=/(iPad|iPhone|iPod)/g.test(navigator.userAgent),(!s||s===document.documentElement)&&(s=window),typeof a=="number"&&typeof l!="function"?l=mg:typeof l=="function"&&typeof a!="number"&&(a=1),this.options={wrapper:s,content:t,eventsTarget:e,smoothWheel:n,syncTouch:i,syncTouchLerp:r,touchInertiaExponent:o,duration:a,easing:l,lerp:c,infinite:h,gestureOrientation:f,orientation:u,touchMultiplier:d,wheelMultiplier:g,autoResize:_,prevent:m,virtualScroll:p,overscroll:S,autoRaf:y,anchors:v,autoToggle:E,allowNestedScroll:A,naiveDimensions:R,stopInertiaOnNavigate:M,respectReducedMotion:x},this.dimensions=new Cx(s,t,{autoResize:_}),this.updateClassName(),this.targetScroll=this.animatedScroll=this.actualScroll,this.options.wrapper.addEventListener("scroll",this.onNativeScroll),this.options.wrapper.addEventListener("scrollend",this.onScrollEnd,{capture:!0}),(this.options.anchors||this.options.stopInertiaOnNavigate)&&this.options.wrapper.addEventListener("click",this.onClick),this.options.wrapper.addEventListener("pointerdown",this.onPointerDown),this.virtualScroll=new Px(e,{touchMultiplier:d,wheelMultiplier:g}),this.virtualScroll.on("scroll",this.onVirtualScroll),this.options.autoToggle&&(this.checkOverflow(),this.rootElement.addEventListener("transitionend",this.onTransitionEnd)),this.options.autoRaf&&(this._rafId=requestAnimationFrame(this.raf))}destroy(){this.emitter.destroy(),this._resetVelocityTimeout!==null&&(clearTimeout(this._resetVelocityTimeout),this._resetVelocityTimeout=null),this.options.wrapper.removeEventListener("scroll",this.onNativeScroll),this.options.wrapper.removeEventListener("scrollend",this.onScrollEnd,{capture:!0}),this.options.wrapper.removeEventListener("pointerdown",this.onPointerDown),(this.options.anchors||this.options.stopInertiaOnNavigate)&&this.options.wrapper.removeEventListener("click",this.onClick),this.virtualScroll.destroy(),this.dimensions.destroy(),this.cleanUpClassName(),this._rafId&&cancelAnimationFrame(this._rafId)}on(s,t){return this.emitter.on(s,t)}off(s,t){return this.emitter.off(s,t)}get overflow(){let s=this.isHorizontal?"overflow-x":"overflow-y";return getComputedStyle(this.rootElement)[s]}checkOverflow(){["hidden","clip"].includes(this.overflow)?this.internalStop():this.internalStart()}setScroll(s){this.isHorizontal?this.options.wrapper.scrollTo({left:s,behavior:"instant"}):this.options.wrapper.scrollTo({top:s,behavior:"instant"})}isTouchOnSelectionHandle(s){let t=window.getSelection();if(!t||t.isCollapsed||t.rangeCount===0)return!1;let e=s.targetTouches[0]??s.changedTouches[0];if(!e)return!1;let n=t.getRangeAt(0).getClientRects();if(n.length===0)return!1;let i=n[0],r=n[n.length-1],o=40,a=Math.hypot(e.clientX-i.left,e.clientY-i.top)<=o,l=Math.hypot(e.clientX-r.right,e.clientY-r.bottom)<=o;return a||l}resize(){this.dimensions.resize(),this.animatedScroll=this.targetScroll=this.actualScroll,this.emit()}emit(){this.emitter.emit("scroll",this)}reset(){this.isLocked=!1,this.isScrolling=!1,this.animatedScroll=this.targetScroll=this.actualScroll,this.lastVelocity=this.velocity=0,this.animate.stop()}start(){if(this.isStopped){if(this.options.autoToggle){this.rootElement.style.removeProperty("overflow");return}this.internalStart()}}internalStart(){this.isStopped&&(this.reset(),this.isStopped=!1,this.emit())}stop(){if(!this.isStopped){if(this.options.autoToggle){this.rootElement.style.setProperty("overflow","clip");return}this.internalStop()}}internalStop(){this.isStopped||(this.reset(),this.isStopped=!0,this.emit())}scrollTo(s,{offset:t=0,immediate:e=!1,lock:n=!1,programmatic:i=!0,lerp:r=i?this.options.lerp:void 0,duration:o=i?this.options.duration:void 0,easing:a=i?this.options.easing:void 0,onStart:l,onComplete:c,force:h=!1,userData:u}={}){if(this.prefersReducedMotion&&(i?e=!0:(r=1,o=void 0,a=void 0)),(this.isStopped||this.isLocked)&&!h)return;let f=s,d=t;if(typeof f=="string"&&["top","left","start","#"].includes(f))f=0;else if(typeof f=="string"&&["bottom","right","end"].includes(f))f=this.limit;else{let g=null;if(typeof f=="string"?(g=f.startsWith("#")?document.getElementById(f.slice(1)):document.querySelector(f),g||(f==="#top"?f=0:console.warn("Lenis: Target not found",f))):f instanceof Element&&(g=f),g){if(this.options.wrapper!==window){let v=this.rootElement.getBoundingClientRect();d-=this.isHorizontal?v.left:v.top}let _=g.getBoundingClientRect(),m=getComputedStyle(g),p=this.isHorizontal?Number.parseFloat(m.scrollMarginLeft):Number.parseFloat(m.scrollMarginTop),S=getComputedStyle(this.rootElement),y=this.isHorizontal?Number.parseFloat(S.scrollPaddingLeft):Number.parseFloat(S.scrollPaddingTop);f=(this.isHorizontal?_.left:_.top)+this.animatedScroll-(Number.isNaN(p)?0:p)-(Number.isNaN(y)?0:y)}}if(typeof f=="number"){if(f+=d,this.options.infinite){if(i){this.targetScroll=this.animatedScroll=this.scroll;let g=f-this.animatedScroll;g>this.limit/2?f-=this.limit:g<-this.limit/2&&(f+=this.limit)}}else f=gg(0,f,this.limit);if(f===this.targetScroll){l?.(this),c?.(this);return}if(this.userData=u??{},e){this.animatedScroll=this.targetScroll=f,this.setScroll(this.scroll),this.reset(),this.preventNextNativeScrollEvent(),this.emit(),c?.(this),this.userData={},requestAnimationFrame(()=>{this.dispatchScrollendEvent()});return}i||(this.targetScroll=f),typeof o=="number"&&typeof a!="function"?a=mg:typeof a=="function"&&typeof o!="number"&&(o=1),this.animate.fromTo(this.animatedScroll,f,{duration:o,easing:a,lerp:r,onStart:()=>{n&&(this.isLocked=!0),this.isScrolling="smooth",l?.(this)},onUpdate:(g,_)=>{this.isScrolling="smooth",this.lastVelocity=this.velocity,this.velocity=g-this.animatedScroll,this.direction=Math.sign(this.velocity),this.animatedScroll=g,this.setScroll(this.scroll),i&&(this.targetScroll=g),_||this.emit(),_&&(this.reset(),this.emit(),c?.(this),this.userData={},requestAnimationFrame(()=>{this.dispatchScrollendEvent()}),this.preventNextNativeScrollEvent())}})}}preventNextNativeScrollEvent(){this._preventNextNativeScrollEvent=!0,requestAnimationFrame(()=>{this._preventNextNativeScrollEvent=!1})}hasNestedScroll(s,{deltaX:t,deltaY:e}){let n=Date.now();s._lenis||(s._lenis={});let i=s._lenis,r,o,a,l,c,h,u,f,d,g;if(n-(i.time??0)>2e3){i.time=Date.now();let A=window.getComputedStyle(s);if(i.computedStyle=A,r=["auto","overlay","scroll"].includes(A.overflowX),o=["auto","overlay","scroll"].includes(A.overflowY),c=["auto"].includes(A.overscrollBehaviorX),h=["auto"].includes(A.overscrollBehaviorY),i.hasOverflowX=r,i.hasOverflowY=o,!(r||o))return!1;u=s.scrollWidth,f=s.scrollHeight,d=s.clientWidth,g=s.clientHeight,a=u>d,l=f>g,i.isScrollableX=a,i.isScrollableY=l,i.scrollWidth=u,i.scrollHeight=f,i.clientWidth=d,i.clientHeight=g,i.hasOverscrollBehaviorX=c,i.hasOverscrollBehaviorY=h}else a=i.isScrollableX,l=i.isScrollableY,r=i.hasOverflowX,o=i.hasOverflowY,u=i.scrollWidth,f=i.scrollHeight,d=i.clientWidth,g=i.clientHeight,c=i.hasOverscrollBehaviorX,h=i.hasOverscrollBehaviorY;if(!(r&&a||o&&l))return!1;let _=Math.abs(t)>=Math.abs(e)?"horizontal":"vertical",m,p,S,y,v,E;if(_==="horizontal")m=Math.round(s.scrollLeft),p=u-d,S=t,y=r,v=a,E=c;else if(_==="vertical")m=Math.round(s.scrollTop),p=f-g,S=e,y=o,v=l,E=h;else return!1;return!E&&(m>=p||m<=0)?!0:(S>0?m<p:m>0)&&y&&v}get rootElement(){return this.options.wrapper===window?document.documentElement:this.options.wrapper}get limit(){return this.options.naiveDimensions?this.isHorizontal?this.rootElement.scrollWidth-this.rootElement.clientWidth:this.rootElement.scrollHeight-this.rootElement.clientHeight:this.dimensions.limit[this.isHorizontal?"x":"y"]}get isHorizontal(){return this.options.orientation==="horizontal"}get actualScroll(){let s=this.options.wrapper;return this.isHorizontal?s.scrollX??s.scrollLeft:s.scrollY??s.scrollTop}get scroll(){return this.options.infinite?Tx(this.animatedScroll,this.limit):this.animatedScroll}get progress(){return this.limit===0?1:this.scroll/this.limit}get isScrolling(){return this._isScrolling}set isScrolling(s){this._isScrolling!==s&&(this._isScrolling=s,this.updateClassName())}get isStopped(){return this._isStopped}set isStopped(s){this._isStopped!==s&&(this._isStopped=s,this.updateClassName())}get isLocked(){return this._isLocked}set isLocked(s){this._isLocked!==s&&(this._isLocked=s,this.updateClassName())}get isSmooth(){return this.isScrolling==="smooth"}get prefersReducedMotion(){return this.options.respectReducedMotion&&this.reducedMotionMediaQuery.matches}get className(){let s="lenis";return this.options.autoToggle&&(s+=" lenis-autoToggle"),this.isStopped&&(s+=" lenis-stopped"),this.isLocked&&(s+=" lenis-locked"),this.isScrolling&&(s+=" lenis-scrolling"),this.isScrolling==="smooth"&&(s+=" lenis-smooth"),s}updateClassName(){this.cleanUpClassName(),this.className.split(" ").forEach(s=>{this.rootElement.classList.add(s)})}cleanUpClassName(){for(let s of Array.from(this.rootElement.classList))(s==="lenis"||s.startsWith("lenis-"))&&this.rootElement.classList.remove(s)}};var Ix=0,xg=1,Lx=2;var C_=1,Dx=2,ns=3,Bs=0,wn=1,pi=2,ki=0,yo=1,Mc=2,yg=3,Mg=4,Ux=5,gr=100,Nx=101,Ox=102,Fx=103,Bx=104,kx=200,zx=201,Vx=202,Hx=203,af=204,lf=205,Gx=206,Wx=207,Xx=208,Yx=209,qx=210,Zx=211,$x=212,Jx=213,Kx=214,cf=0,hf=1,uf=2,wo=3,ff=4,df=5,pf=6,mf=7,R_=0,Qx=1,jx=2,Os=0,Dd=1,Ud=2,Nd=3,qa=4,ty=5,Od=6,Fd=7;var P_=300,To=301,Eo=302,gf=303,_f=304,Zc=306,vf=1e3,xr=1001,xf=1002,jn=1003,ey=1004;var Wl=1005;var Fi=1006,Tu=1007;var yr=1008;var os=1009,I_=1010,L_=1011,za=1012,Bd=1013,Mr=1014,Bi=1015,ei=1016,kd=1017,zd=1018,Ao=1020,D_=35902,U_=1021,N_=1022,bi=1023,O_=1024,F_=1025,Mo=1026,Co=1027,Vd=1028,Hd=1029,B_=1030,Gd=1031;var Wd=1033,gc=33776,_c=33777,vc=33778,xc=33779,yf=35840,Mf=35841,Sf=35842,bf=35843,wf=36196,Tf=37492,Ef=37496,Af=37808,Cf=37809,Rf=37810,Pf=37811,If=37812,Lf=37813,Df=37814,Uf=37815,Nf=37816,Of=37817,Ff=37818,Bf=37819,kf=37820,zf=37821,yc=36492,Vf=36494,Hf=36495,k_=36283,Gf=36284,Wf=36285,Xf=36286;var Sc=2300,Yf=2301,Eu=2302,Sg=2400,bg=2401,wg=2402;var ny=3200,iy=3201;var z_=0,sy=1,Us="",Mn="srgb",Oo="srgb-linear",$c="linear",we="srgb";var no=7680;var Tg=519,ry=512,oy=513,ay=514,V_=515,ly=516,cy=517,hy=518,uy=519,Eg=35044,Xd=35048;var Ag="300 es",ss=2e3,bc=2001,ks=class{addEventListener(t,e){this._listeners===void 0&&(this._listeners={});let n=this._listeners;n[t]===void 0&&(n[t]=[]),n[t].indexOf(e)===-1&&n[t].push(e)}hasEventListener(t,e){if(this._listeners===void 0)return!1;let n=this._listeners;return n[t]!==void 0&&n[t].indexOf(e)!==-1}removeEventListener(t,e){if(this._listeners===void 0)return;let i=this._listeners[t];if(i!==void 0){let r=i.indexOf(e);r!==-1&&i.splice(r,1)}}dispatchEvent(t){if(this._listeners===void 0)return;let n=this._listeners[t.type];if(n!==void 0){t.target=this;let i=n.slice(0);for(let r=0,o=i.length;r<o;r++)i[r].call(this,t);t.target=null}}},xn=["00","01","02","03","04","05","06","07","08","09","0a","0b","0c","0d","0e","0f","10","11","12","13","14","15","16","17","18","19","1a","1b","1c","1d","1e","1f","20","21","22","23","24","25","26","27","28","29","2a","2b","2c","2d","2e","2f","30","31","32","33","34","35","36","37","38","39","3a","3b","3c","3d","3e","3f","40","41","42","43","44","45","46","47","48","49","4a","4b","4c","4d","4e","4f","50","51","52","53","54","55","56","57","58","59","5a","5b","5c","5d","5e","5f","60","61","62","63","64","65","66","67","68","69","6a","6b","6c","6d","6e","6f","70","71","72","73","74","75","76","77","78","79","7a","7b","7c","7d","7e","7f","80","81","82","83","84","85","86","87","88","89","8a","8b","8c","8d","8e","8f","90","91","92","93","94","95","96","97","98","99","9a","9b","9c","9d","9e","9f","a0","a1","a2","a3","a4","a5","a6","a7","a8","a9","aa","ab","ac","ad","ae","af","b0","b1","b2","b3","b4","b5","b6","b7","b8","b9","ba","bb","bc","bd","be","bf","c0","c1","c2","c3","c4","c5","c6","c7","c8","c9","ca","cb","cc","cd","ce","cf","d0","d1","d2","d3","d4","d5","d6","d7","d8","d9","da","db","dc","dd","de","df","e0","e1","e2","e3","e4","e5","e6","e7","e8","e9","ea","eb","ec","ed","ee","ef","f0","f1","f2","f3","f4","f5","f6","f7","f8","f9","fa","fb","fc","fd","fe","ff"];var Au=Math.PI/180,qf=180/Math.PI;function Fo(){let s=Math.random()*4294967295|0,t=Math.random()*4294967295|0,e=Math.random()*4294967295|0,n=Math.random()*4294967295|0;return(xn[s&255]+xn[s>>8&255]+xn[s>>16&255]+xn[s>>24&255]+"-"+xn[t&255]+xn[t>>8&255]+"-"+xn[t>>16&15|64]+xn[t>>24&255]+"-"+xn[e&63|128]+xn[e>>8&255]+"-"+xn[e>>16&255]+xn[e>>24&255]+xn[n&255]+xn[n>>8&255]+xn[n>>16&255]+xn[n>>24&255]).toLowerCase()}function Sn(s,t,e){return Math.max(t,Math.min(e,s))}function fy(s,t){return(s%t+t)%t}function Cu(s,t,e){return(1-e)*s+e*t}function Aa(s,t){switch(t.constructor){case Float32Array:return s;case Uint32Array:return s/4294967295;case Uint16Array:return s/65535;case Uint8Array:return s/255;case Int32Array:return Math.max(s/2147483647,-1);case Int16Array:return Math.max(s/32767,-1);case Int8Array:return Math.max(s/127,-1);default:throw new Error("Invalid component type.")}}function zn(s,t){switch(t.constructor){case Float32Array:return s;case Uint32Array:return Math.round(s*4294967295);case Uint16Array:return Math.round(s*65535);case Uint8Array:return Math.round(s*255);case Int32Array:return Math.round(s*2147483647);case Int16Array:return Math.round(s*32767);case Int8Array:return Math.round(s*127);default:throw new Error("Invalid component type.")}}var vt=class s{constructor(t=0,e=0){s.prototype.isVector2=!0,this.x=t,this.y=e}get width(){return this.x}set width(t){this.x=t}get height(){return this.y}set height(t){this.y=t}set(t,e){return this.x=t,this.y=e,this}setScalar(t){return this.x=t,this.y=t,this}setX(t){return this.x=t,this}setY(t){return this.y=t,this}setComponent(t,e){switch(t){case 0:this.x=e;break;case 1:this.y=e;break;default:throw new Error("index is out of range: "+t)}return this}getComponent(t){switch(t){case 0:return this.x;case 1:return this.y;default:throw new Error("index is out of range: "+t)}}clone(){return new this.constructor(this.x,this.y)}copy(t){return this.x=t.x,this.y=t.y,this}add(t){return this.x+=t.x,this.y+=t.y,this}addScalar(t){return this.x+=t,this.y+=t,this}addVectors(t,e){return this.x=t.x+e.x,this.y=t.y+e.y,this}addScaledVector(t,e){return this.x+=t.x*e,this.y+=t.y*e,this}sub(t){return this.x-=t.x,this.y-=t.y,this}subScalar(t){return this.x-=t,this.y-=t,this}subVectors(t,e){return this.x=t.x-e.x,this.y=t.y-e.y,this}multiply(t){return this.x*=t.x,this.y*=t.y,this}multiplyScalar(t){return this.x*=t,this.y*=t,this}divide(t){return this.x/=t.x,this.y/=t.y,this}divideScalar(t){return this.multiplyScalar(1/t)}applyMatrix3(t){let e=this.x,n=this.y,i=t.elements;return this.x=i[0]*e+i[3]*n+i[6],this.y=i[1]*e+i[4]*n+i[7],this}min(t){return this.x=Math.min(this.x,t.x),this.y=Math.min(this.y,t.y),this}max(t){return this.x=Math.max(this.x,t.x),this.y=Math.max(this.y,t.y),this}clamp(t,e){return this.x=Math.max(t.x,Math.min(e.x,this.x)),this.y=Math.max(t.y,Math.min(e.y,this.y)),this}clampScalar(t,e){return this.x=Math.max(t,Math.min(e,this.x)),this.y=Math.max(t,Math.min(e,this.y)),this}clampLength(t,e){let n=this.length();return this.divideScalar(n||1).multiplyScalar(Math.max(t,Math.min(e,n)))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this}negate(){return this.x=-this.x,this.y=-this.y,this}dot(t){return this.x*t.x+this.y*t.y}cross(t){return this.x*t.y-this.y*t.x}lengthSq(){return this.x*this.x+this.y*this.y}length(){return Math.sqrt(this.x*this.x+this.y*this.y)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)}normalize(){return this.divideScalar(this.length()||1)}angle(){return Math.atan2(-this.y,-this.x)+Math.PI}angleTo(t){let e=Math.sqrt(this.lengthSq()*t.lengthSq());if(e===0)return Math.PI/2;let n=this.dot(t)/e;return Math.acos(Sn(n,-1,1))}distanceTo(t){return Math.sqrt(this.distanceToSquared(t))}distanceToSquared(t){let e=this.x-t.x,n=this.y-t.y;return e*e+n*n}manhattanDistanceTo(t){return Math.abs(this.x-t.x)+Math.abs(this.y-t.y)}setLength(t){return this.normalize().multiplyScalar(t)}lerp(t,e){return this.x+=(t.x-this.x)*e,this.y+=(t.y-this.y)*e,this}lerpVectors(t,e,n){return this.x=t.x+(e.x-t.x)*n,this.y=t.y+(e.y-t.y)*n,this}equals(t){return t.x===this.x&&t.y===this.y}fromArray(t,e=0){return this.x=t[e],this.y=t[e+1],this}toArray(t=[],e=0){return t[e]=this.x,t[e+1]=this.y,t}fromBufferAttribute(t,e){return this.x=t.getX(e),this.y=t.getY(e),this}rotateAround(t,e){let n=Math.cos(e),i=Math.sin(e),r=this.x-t.x,o=this.y-t.y;return this.x=r*n-o*i+t.x,this.y=r*i+o*n+t.y,this}random(){return this.x=Math.random(),this.y=Math.random(),this}*[Symbol.iterator](){yield this.x,yield this.y}},oe=class s{constructor(t,e,n,i,r,o,a,l,c){s.prototype.isMatrix3=!0,this.elements=[1,0,0,0,1,0,0,0,1],t!==void 0&&this.set(t,e,n,i,r,o,a,l,c)}set(t,e,n,i,r,o,a,l,c){let h=this.elements;return h[0]=t,h[1]=i,h[2]=a,h[3]=e,h[4]=r,h[5]=l,h[6]=n,h[7]=o,h[8]=c,this}identity(){return this.set(1,0,0,0,1,0,0,0,1),this}copy(t){let e=this.elements,n=t.elements;return e[0]=n[0],e[1]=n[1],e[2]=n[2],e[3]=n[3],e[4]=n[4],e[5]=n[5],e[6]=n[6],e[7]=n[7],e[8]=n[8],this}extractBasis(t,e,n){return t.setFromMatrix3Column(this,0),e.setFromMatrix3Column(this,1),n.setFromMatrix3Column(this,2),this}setFromMatrix4(t){let e=t.elements;return this.set(e[0],e[4],e[8],e[1],e[5],e[9],e[2],e[6],e[10]),this}multiply(t){return this.multiplyMatrices(this,t)}premultiply(t){return this.multiplyMatrices(t,this)}multiplyMatrices(t,e){let n=t.elements,i=e.elements,r=this.elements,o=n[0],a=n[3],l=n[6],c=n[1],h=n[4],u=n[7],f=n[2],d=n[5],g=n[8],_=i[0],m=i[3],p=i[6],S=i[1],y=i[4],v=i[7],E=i[2],A=i[5],T=i[8];return r[0]=o*_+a*S+l*E,r[3]=o*m+a*y+l*A,r[6]=o*p+a*v+l*T,r[1]=c*_+h*S+u*E,r[4]=c*m+h*y+u*A,r[7]=c*p+h*v+u*T,r[2]=f*_+d*S+g*E,r[5]=f*m+d*y+g*A,r[8]=f*p+d*v+g*T,this}multiplyScalar(t){let e=this.elements;return e[0]*=t,e[3]*=t,e[6]*=t,e[1]*=t,e[4]*=t,e[7]*=t,e[2]*=t,e[5]*=t,e[8]*=t,this}determinant(){let t=this.elements,e=t[0],n=t[1],i=t[2],r=t[3],o=t[4],a=t[5],l=t[6],c=t[7],h=t[8];return e*o*h-e*a*c-n*r*h+n*a*l+i*r*c-i*o*l}invert(){let t=this.elements,e=t[0],n=t[1],i=t[2],r=t[3],o=t[4],a=t[5],l=t[6],c=t[7],h=t[8],u=h*o-a*c,f=a*l-h*r,d=c*r-o*l,g=e*u+n*f+i*d;if(g===0)return this.set(0,0,0,0,0,0,0,0,0);let _=1/g;return t[0]=u*_,t[1]=(i*c-h*n)*_,t[2]=(a*n-i*o)*_,t[3]=f*_,t[4]=(h*e-i*l)*_,t[5]=(i*r-a*e)*_,t[6]=d*_,t[7]=(n*l-c*e)*_,t[8]=(o*e-n*r)*_,this}transpose(){let t,e=this.elements;return t=e[1],e[1]=e[3],e[3]=t,t=e[2],e[2]=e[6],e[6]=t,t=e[5],e[5]=e[7],e[7]=t,this}getNormalMatrix(t){return this.setFromMatrix4(t).invert().transpose()}transposeIntoArray(t){let e=this.elements;return t[0]=e[0],t[1]=e[3],t[2]=e[6],t[3]=e[1],t[4]=e[4],t[5]=e[7],t[6]=e[2],t[7]=e[5],t[8]=e[8],this}setUvTransform(t,e,n,i,r,o,a){let l=Math.cos(r),c=Math.sin(r);return this.set(n*l,n*c,-n*(l*o+c*a)+o+t,-i*c,i*l,-i*(-c*o+l*a)+a+e,0,0,1),this}scale(t,e){return this.premultiply(Ru.makeScale(t,e)),this}rotate(t){return this.premultiply(Ru.makeRotation(-t)),this}translate(t,e){return this.premultiply(Ru.makeTranslation(t,e)),this}makeTranslation(t,e){return t.isVector2?this.set(1,0,t.x,0,1,t.y,0,0,1):this.set(1,0,t,0,1,e,0,0,1),this}makeRotation(t){let e=Math.cos(t),n=Math.sin(t);return this.set(e,-n,0,n,e,0,0,0,1),this}makeScale(t,e){return this.set(t,0,0,0,e,0,0,0,1),this}equals(t){let e=this.elements,n=t.elements;for(let i=0;i<9;i++)if(e[i]!==n[i])return!1;return!0}fromArray(t,e=0){for(let n=0;n<9;n++)this.elements[n]=t[n+e];return this}toArray(t=[],e=0){let n=this.elements;return t[e]=n[0],t[e+1]=n[1],t[e+2]=n[2],t[e+3]=n[3],t[e+4]=n[4],t[e+5]=n[5],t[e+6]=n[6],t[e+7]=n[7],t[e+8]=n[8],t}clone(){return new this.constructor().fromArray(this.elements)}},Ru=new oe;function H_(s){for(let t=s.length-1;t>=0;--t)if(s[t]>=65535)return!0;return!1}function wc(s){return document.createElementNS("http://www.w3.org/1999/xhtml",s)}function dy(){let s=wc("canvas");return s.style.display="block",s}var Cg={};function Na(s){s in Cg||(Cg[s]=!0,console.warn(s))}function py(s,t,e){return new Promise(function(n,i){function r(){switch(s.clientWaitSync(t,s.SYNC_FLUSH_COMMANDS_BIT,0)){case s.WAIT_FAILED:i();break;case s.TIMEOUT_EXPIRED:setTimeout(r,e);break;default:n()}}setTimeout(r,e)})}function my(s){let t=s.elements;t[2]=.5*t[2]+.5*t[3],t[6]=.5*t[6]+.5*t[7],t[10]=.5*t[10]+.5*t[11],t[14]=.5*t[14]+.5*t[15]}function gy(s){let t=s.elements;t[11]===-1?(t[10]=-t[10]-1,t[14]=-t[14]):(t[10]=-t[10],t[14]=-t[14]+1)}var ge={enabled:!0,workingColorSpace:Oo,spaces:{},convert:function(s,t,e){return this.enabled===!1||t===e||!t||!e||(this.spaces[t].transfer===we&&(s.r=rs(s.r),s.g=rs(s.g),s.b=rs(s.b)),this.spaces[t].primaries!==this.spaces[e].primaries&&(s.applyMatrix3(this.spaces[t].toXYZ),s.applyMatrix3(this.spaces[e].fromXYZ)),this.spaces[e].transfer===we&&(s.r=So(s.r),s.g=So(s.g),s.b=So(s.b))),s},fromWorkingColorSpace:function(s,t){return this.convert(s,this.workingColorSpace,t)},toWorkingColorSpace:function(s,t){return this.convert(s,t,this.workingColorSpace)},getPrimaries:function(s){return this.spaces[s].primaries},getTransfer:function(s){return s===Us?$c:this.spaces[s].transfer},getLuminanceCoefficients:function(s,t=this.workingColorSpace){return s.fromArray(this.spaces[t].luminanceCoefficients)},define:function(s){Object.assign(this.spaces,s)},_getMatrix:function(s,t,e){return s.copy(this.spaces[t].toXYZ).multiply(this.spaces[e].fromXYZ)},_getDrawingBufferColorSpace:function(s){return this.spaces[s].outputColorSpaceConfig.drawingBufferColorSpace},_getUnpackColorSpace:function(s=this.workingColorSpace){return this.spaces[s].workingColorSpaceConfig.unpackColorSpace}};function rs(s){return s<.04045?s*.0773993808:Math.pow(s*.9478672986+.0521327014,2.4)}function So(s){return s<.0031308?s*12.92:1.055*Math.pow(s,.41666)-.055}var Rg=[.64,.33,.3,.6,.15,.06],Pg=[.2126,.7152,.0722],Ig=[.3127,.329],Lg=new oe().set(.4123908,.3575843,.1804808,.212639,.7151687,.0721923,.0193308,.1191948,.9505322),Dg=new oe().set(3.2409699,-1.5373832,-.4986108,-.9692436,1.8759675,.0415551,.0556301,-.203977,1.0569715);ge.define({[Oo]:{primaries:Rg,whitePoint:Ig,transfer:$c,toXYZ:Lg,fromXYZ:Dg,luminanceCoefficients:Pg,workingColorSpaceConfig:{unpackColorSpace:Mn},outputColorSpaceConfig:{drawingBufferColorSpace:Mn}},[Mn]:{primaries:Rg,whitePoint:Ig,transfer:we,toXYZ:Lg,fromXYZ:Dg,luminanceCoefficients:Pg,outputColorSpaceConfig:{drawingBufferColorSpace:Mn}}});var io,Zf=class{static getDataURL(t){if(/^data:/i.test(t.src)||typeof HTMLCanvasElement>"u")return t.src;let e;if(t instanceof HTMLCanvasElement)e=t;else{io===void 0&&(io=wc("canvas")),io.width=t.width,io.height=t.height;let n=io.getContext("2d");t instanceof ImageData?n.putImageData(t,0,0):n.drawImage(t,0,0,t.width,t.height),e=io}return e.width>2048||e.height>2048?(console.warn("THREE.ImageUtils.getDataURL: Image converted to jpg for performance reasons",t),e.toDataURL("image/jpeg",.6)):e.toDataURL("image/png")}static sRGBToLinear(t){if(typeof HTMLImageElement<"u"&&t instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&t instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&t instanceof ImageBitmap){let e=wc("canvas");e.width=t.width,e.height=t.height;let n=e.getContext("2d");n.drawImage(t,0,0,t.width,t.height);let i=n.getImageData(0,0,t.width,t.height),r=i.data;for(let o=0;o<r.length;o++)r[o]=rs(r[o]/255)*255;return n.putImageData(i,0,0),e}else if(t.data){let e=t.data.slice(0);for(let n=0;n<e.length;n++)e instanceof Uint8Array||e instanceof Uint8ClampedArray?e[n]=Math.floor(rs(e[n]/255)*255):e[n]=rs(e[n]);return{data:e,width:t.width,height:t.height}}else return console.warn("THREE.ImageUtils.sRGBToLinear(): Unsupported image type. No color space conversion applied."),t}},_y=0,Tc=class{constructor(t=null){this.isSource=!0,Object.defineProperty(this,"id",{value:_y++}),this.uuid=Fo(),this.data=t,this.dataReady=!0,this.version=0}set needsUpdate(t){t===!0&&this.version++}toJSON(t){let e=t===void 0||typeof t=="string";if(!e&&t.images[this.uuid]!==void 0)return t.images[this.uuid];let n={uuid:this.uuid,url:""},i=this.data;if(i!==null){let r;if(Array.isArray(i)){r=[];for(let o=0,a=i.length;o<a;o++)i[o].isDataTexture?r.push(Pu(i[o].image)):r.push(Pu(i[o]))}else r=Pu(i);n.url=r}return e||(t.images[this.uuid]=n),n}};function Pu(s){return typeof HTMLImageElement<"u"&&s instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&s instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&s instanceof ImageBitmap?Zf.getDataURL(s):s.data?{data:Array.from(s.data),width:s.width,height:s.height,type:s.data.constructor.name}:(console.warn("THREE.Texture: Unable to serialize Texture."),{})}var vy=0,Vn=class s extends ks{constructor(t=s.DEFAULT_IMAGE,e=s.DEFAULT_MAPPING,n=xr,i=xr,r=Fi,o=yr,a=bi,l=os,c=s.DEFAULT_ANISOTROPY,h=Us){super(),this.isTexture=!0,Object.defineProperty(this,"id",{value:vy++}),this.uuid=Fo(),this.name="",this.source=new Tc(t),this.mipmaps=[],this.mapping=e,this.channel=0,this.wrapS=n,this.wrapT=i,this.magFilter=r,this.minFilter=o,this.anisotropy=c,this.format=a,this.internalFormat=null,this.type=l,this.offset=new vt(0,0),this.repeat=new vt(1,1),this.center=new vt(0,0),this.rotation=0,this.matrixAutoUpdate=!0,this.matrix=new oe,this.generateMipmaps=!0,this.premultiplyAlpha=!1,this.flipY=!0,this.unpackAlignment=4,this.colorSpace=h,this.userData={},this.version=0,this.onUpdate=null,this.isRenderTargetTexture=!1,this.pmremVersion=0}get image(){return this.source.data}set image(t=null){this.source.data=t}updateMatrix(){this.matrix.setUvTransform(this.offset.x,this.offset.y,this.repeat.x,this.repeat.y,this.rotation,this.center.x,this.center.y)}clone(){return new this.constructor().copy(this)}copy(t){return this.name=t.name,this.source=t.source,this.mipmaps=t.mipmaps.slice(0),this.mapping=t.mapping,this.channel=t.channel,this.wrapS=t.wrapS,this.wrapT=t.wrapT,this.magFilter=t.magFilter,this.minFilter=t.minFilter,this.anisotropy=t.anisotropy,this.format=t.format,this.internalFormat=t.internalFormat,this.type=t.type,this.offset.copy(t.offset),this.repeat.copy(t.repeat),this.center.copy(t.center),this.rotation=t.rotation,this.matrixAutoUpdate=t.matrixAutoUpdate,this.matrix.copy(t.matrix),this.generateMipmaps=t.generateMipmaps,this.premultiplyAlpha=t.premultiplyAlpha,this.flipY=t.flipY,this.unpackAlignment=t.unpackAlignment,this.colorSpace=t.colorSpace,this.userData=JSON.parse(JSON.stringify(t.userData)),this.needsUpdate=!0,this}toJSON(t){let e=t===void 0||typeof t=="string";if(!e&&t.textures[this.uuid]!==void 0)return t.textures[this.uuid];let n={metadata:{version:4.6,type:"Texture",generator:"Texture.toJSON"},uuid:this.uuid,name:this.name,image:this.source.toJSON(t).uuid,mapping:this.mapping,channel:this.channel,repeat:[this.repeat.x,this.repeat.y],offset:[this.offset.x,this.offset.y],center:[this.center.x,this.center.y],rotation:this.rotation,wrap:[this.wrapS,this.wrapT],format:this.format,internalFormat:this.internalFormat,type:this.type,colorSpace:this.colorSpace,minFilter:this.minFilter,magFilter:this.magFilter,anisotropy:this.anisotropy,flipY:this.flipY,generateMipmaps:this.generateMipmaps,premultiplyAlpha:this.premultiplyAlpha,unpackAlignment:this.unpackAlignment};return Object.keys(this.userData).length>0&&(n.userData=this.userData),e||(t.textures[this.uuid]=n),n}dispose(){this.dispatchEvent({type:"dispose"})}transformUv(t){if(this.mapping!==P_)return t;if(t.applyMatrix3(this.matrix),t.x<0||t.x>1)switch(this.wrapS){case vf:t.x=t.x-Math.floor(t.x);break;case xr:t.x=t.x<0?0:1;break;case xf:Math.abs(Math.floor(t.x)%2)===1?t.x=Math.ceil(t.x)-t.x:t.x=t.x-Math.floor(t.x);break}if(t.y<0||t.y>1)switch(this.wrapT){case vf:t.y=t.y-Math.floor(t.y);break;case xr:t.y=t.y<0?0:1;break;case xf:Math.abs(Math.floor(t.y)%2)===1?t.y=Math.ceil(t.y)-t.y:t.y=t.y-Math.floor(t.y);break}return this.flipY&&(t.y=1-t.y),t}set needsUpdate(t){t===!0&&(this.version++,this.source.needsUpdate=!0)}set needsPMREMUpdate(t){t===!0&&this.pmremVersion++}};Vn.DEFAULT_IMAGE=null;Vn.DEFAULT_MAPPING=P_;Vn.DEFAULT_ANISOTROPY=1;var Ae=class s{constructor(t=0,e=0,n=0,i=1){s.prototype.isVector4=!0,this.x=t,this.y=e,this.z=n,this.w=i}get width(){return this.z}set width(t){this.z=t}get height(){return this.w}set height(t){this.w=t}set(t,e,n,i){return this.x=t,this.y=e,this.z=n,this.w=i,this}setScalar(t){return this.x=t,this.y=t,this.z=t,this.w=t,this}setX(t){return this.x=t,this}setY(t){return this.y=t,this}setZ(t){return this.z=t,this}setW(t){return this.w=t,this}setComponent(t,e){switch(t){case 0:this.x=e;break;case 1:this.y=e;break;case 2:this.z=e;break;case 3:this.w=e;break;default:throw new Error("index is out of range: "+t)}return this}getComponent(t){switch(t){case 0:return this.x;case 1:return this.y;case 2:return this.z;case 3:return this.w;default:throw new Error("index is out of range: "+t)}}clone(){return new this.constructor(this.x,this.y,this.z,this.w)}copy(t){return this.x=t.x,this.y=t.y,this.z=t.z,this.w=t.w!==void 0?t.w:1,this}add(t){return this.x+=t.x,this.y+=t.y,this.z+=t.z,this.w+=t.w,this}addScalar(t){return this.x+=t,this.y+=t,this.z+=t,this.w+=t,this}addVectors(t,e){return this.x=t.x+e.x,this.y=t.y+e.y,this.z=t.z+e.z,this.w=t.w+e.w,this}addScaledVector(t,e){return this.x+=t.x*e,this.y+=t.y*e,this.z+=t.z*e,this.w+=t.w*e,this}sub(t){return this.x-=t.x,this.y-=t.y,this.z-=t.z,this.w-=t.w,this}subScalar(t){return this.x-=t,this.y-=t,this.z-=t,this.w-=t,this}subVectors(t,e){return this.x=t.x-e.x,this.y=t.y-e.y,this.z=t.z-e.z,this.w=t.w-e.w,this}multiply(t){return this.x*=t.x,this.y*=t.y,this.z*=t.z,this.w*=t.w,this}multiplyScalar(t){return this.x*=t,this.y*=t,this.z*=t,this.w*=t,this}applyMatrix4(t){let e=this.x,n=this.y,i=this.z,r=this.w,o=t.elements;return this.x=o[0]*e+o[4]*n+o[8]*i+o[12]*r,this.y=o[1]*e+o[5]*n+o[9]*i+o[13]*r,this.z=o[2]*e+o[6]*n+o[10]*i+o[14]*r,this.w=o[3]*e+o[7]*n+o[11]*i+o[15]*r,this}divide(t){return this.x/=t.x,this.y/=t.y,this.z/=t.z,this.w/=t.w,this}divideScalar(t){return this.multiplyScalar(1/t)}setAxisAngleFromQuaternion(t){this.w=2*Math.acos(t.w);let e=Math.sqrt(1-t.w*t.w);return e<1e-4?(this.x=1,this.y=0,this.z=0):(this.x=t.x/e,this.y=t.y/e,this.z=t.z/e),this}setAxisAngleFromRotationMatrix(t){let e,n,i,r,l=t.elements,c=l[0],h=l[4],u=l[8],f=l[1],d=l[5],g=l[9],_=l[2],m=l[6],p=l[10];if(Math.abs(h-f)<.01&&Math.abs(u-_)<.01&&Math.abs(g-m)<.01){if(Math.abs(h+f)<.1&&Math.abs(u+_)<.1&&Math.abs(g+m)<.1&&Math.abs(c+d+p-3)<.1)return this.set(1,0,0,0),this;e=Math.PI;let y=(c+1)/2,v=(d+1)/2,E=(p+1)/2,A=(h+f)/4,T=(u+_)/4,R=(g+m)/4;return y>v&&y>E?y<.01?(n=0,i=.707106781,r=.707106781):(n=Math.sqrt(y),i=A/n,r=T/n):v>E?v<.01?(n=.707106781,i=0,r=.707106781):(i=Math.sqrt(v),n=A/i,r=R/i):E<.01?(n=.707106781,i=.707106781,r=0):(r=Math.sqrt(E),n=T/r,i=R/r),this.set(n,i,r,e),this}let S=Math.sqrt((m-g)*(m-g)+(u-_)*(u-_)+(f-h)*(f-h));return Math.abs(S)<.001&&(S=1),this.x=(m-g)/S,this.y=(u-_)/S,this.z=(f-h)/S,this.w=Math.acos((c+d+p-1)/2),this}setFromMatrixPosition(t){let e=t.elements;return this.x=e[12],this.y=e[13],this.z=e[14],this.w=e[15],this}min(t){return this.x=Math.min(this.x,t.x),this.y=Math.min(this.y,t.y),this.z=Math.min(this.z,t.z),this.w=Math.min(this.w,t.w),this}max(t){return this.x=Math.max(this.x,t.x),this.y=Math.max(this.y,t.y),this.z=Math.max(this.z,t.z),this.w=Math.max(this.w,t.w),this}clamp(t,e){return this.x=Math.max(t.x,Math.min(e.x,this.x)),this.y=Math.max(t.y,Math.min(e.y,this.y)),this.z=Math.max(t.z,Math.min(e.z,this.z)),this.w=Math.max(t.w,Math.min(e.w,this.w)),this}clampScalar(t,e){return this.x=Math.max(t,Math.min(e,this.x)),this.y=Math.max(t,Math.min(e,this.y)),this.z=Math.max(t,Math.min(e,this.z)),this.w=Math.max(t,Math.min(e,this.w)),this}clampLength(t,e){let n=this.length();return this.divideScalar(n||1).multiplyScalar(Math.max(t,Math.min(e,n)))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this.z=Math.floor(this.z),this.w=Math.floor(this.w),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this.z=Math.ceil(this.z),this.w=Math.ceil(this.w),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this.z=Math.round(this.z),this.w=Math.round(this.w),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this.z=Math.trunc(this.z),this.w=Math.trunc(this.w),this}negate(){return this.x=-this.x,this.y=-this.y,this.z=-this.z,this.w=-this.w,this}dot(t){return this.x*t.x+this.y*t.y+this.z*t.z+this.w*t.w}lengthSq(){return this.x*this.x+this.y*this.y+this.z*this.z+this.w*this.w}length(){return Math.sqrt(this.x*this.x+this.y*this.y+this.z*this.z+this.w*this.w)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)+Math.abs(this.z)+Math.abs(this.w)}normalize(){return this.divideScalar(this.length()||1)}setLength(t){return this.normalize().multiplyScalar(t)}lerp(t,e){return this.x+=(t.x-this.x)*e,this.y+=(t.y-this.y)*e,this.z+=(t.z-this.z)*e,this.w+=(t.w-this.w)*e,this}lerpVectors(t,e,n){return this.x=t.x+(e.x-t.x)*n,this.y=t.y+(e.y-t.y)*n,this.z=t.z+(e.z-t.z)*n,this.w=t.w+(e.w-t.w)*n,this}equals(t){return t.x===this.x&&t.y===this.y&&t.z===this.z&&t.w===this.w}fromArray(t,e=0){return this.x=t[e],this.y=t[e+1],this.z=t[e+2],this.w=t[e+3],this}toArray(t=[],e=0){return t[e]=this.x,t[e+1]=this.y,t[e+2]=this.z,t[e+3]=this.w,t}fromBufferAttribute(t,e){return this.x=t.getX(e),this.y=t.getY(e),this.z=t.getZ(e),this.w=t.getW(e),this}random(){return this.x=Math.random(),this.y=Math.random(),this.z=Math.random(),this.w=Math.random(),this}*[Symbol.iterator](){yield this.x,yield this.y,yield this.z,yield this.w}},$f=class extends ks{constructor(t=1,e=1,n={}){super(),this.isRenderTarget=!0,this.width=t,this.height=e,this.depth=1,this.scissor=new Ae(0,0,t,e),this.scissorTest=!1,this.viewport=new Ae(0,0,t,e);let i={width:t,height:e,depth:1};n=Object.assign({generateMipmaps:!1,internalFormat:null,minFilter:Fi,depthBuffer:!0,stencilBuffer:!1,resolveDepthBuffer:!0,resolveStencilBuffer:!0,depthTexture:null,samples:0,count:1},n);let r=new Vn(i,n.mapping,n.wrapS,n.wrapT,n.magFilter,n.minFilter,n.format,n.type,n.anisotropy,n.colorSpace);r.flipY=!1,r.generateMipmaps=n.generateMipmaps,r.internalFormat=n.internalFormat,this.textures=[];let o=n.count;for(let a=0;a<o;a++)this.textures[a]=r.clone(),this.textures[a].isRenderTargetTexture=!0;this.depthBuffer=n.depthBuffer,this.stencilBuffer=n.stencilBuffer,this.resolveDepthBuffer=n.resolveDepthBuffer,this.resolveStencilBuffer=n.resolveStencilBuffer,this.depthTexture=n.depthTexture,this.samples=n.samples}get texture(){return this.textures[0]}set texture(t){this.textures[0]=t}setSize(t,e,n=1){if(this.width!==t||this.height!==e||this.depth!==n){this.width=t,this.height=e,this.depth=n;for(let i=0,r=this.textures.length;i<r;i++)this.textures[i].image.width=t,this.textures[i].image.height=e,this.textures[i].image.depth=n;this.dispose()}this.viewport.set(0,0,t,e),this.scissor.set(0,0,t,e)}clone(){return new this.constructor().copy(this)}copy(t){this.width=t.width,this.height=t.height,this.depth=t.depth,this.scissor.copy(t.scissor),this.scissorTest=t.scissorTest,this.viewport.copy(t.viewport),this.textures.length=0;for(let n=0,i=t.textures.length;n<i;n++)this.textures[n]=t.textures[n].clone(),this.textures[n].isRenderTargetTexture=!0;let e=Object.assign({},t.texture.image);return this.texture.source=new Tc(e),this.depthBuffer=t.depthBuffer,this.stencilBuffer=t.stencilBuffer,this.resolveDepthBuffer=t.resolveDepthBuffer,this.resolveStencilBuffer=t.resolveStencilBuffer,t.depthTexture!==null&&(this.depthTexture=t.depthTexture.clone()),this.samples=t.samples,this}dispose(){this.dispatchEvent({type:"dispose"})}},un=class extends $f{constructor(t=1,e=1,n={}){super(t,e,n),this.isWebGLRenderTarget=!0}},Ec=class extends Vn{constructor(t=null,e=1,n=1,i=1){super(null),this.isDataArrayTexture=!0,this.image={data:t,width:e,height:n,depth:i},this.magFilter=jn,this.minFilter=jn,this.wrapR=xr,this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1,this.layerUpdates=new Set}addLayerUpdate(t){this.layerUpdates.add(t)}clearLayerUpdates(){this.layerUpdates.clear()}};var Jf=class extends Vn{constructor(t=null,e=1,n=1,i=1){super(null),this.isData3DTexture=!0,this.image={data:t,width:e,height:n,depth:i},this.magFilter=jn,this.minFilter=jn,this.wrapR=xr,this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1}};var wi=class{constructor(t=0,e=0,n=0,i=1){this.isQuaternion=!0,this._x=t,this._y=e,this._z=n,this._w=i}static slerpFlat(t,e,n,i,r,o,a){let l=n[i+0],c=n[i+1],h=n[i+2],u=n[i+3],f=r[o+0],d=r[o+1],g=r[o+2],_=r[o+3];if(a===0){t[e+0]=l,t[e+1]=c,t[e+2]=h,t[e+3]=u;return}if(a===1){t[e+0]=f,t[e+1]=d,t[e+2]=g,t[e+3]=_;return}if(u!==_||l!==f||c!==d||h!==g){let m=1-a,p=l*f+c*d+h*g+u*_,S=p>=0?1:-1,y=1-p*p;if(y>Number.EPSILON){let E=Math.sqrt(y),A=Math.atan2(E,p*S);m=Math.sin(m*A)/E,a=Math.sin(a*A)/E}let v=a*S;if(l=l*m+f*v,c=c*m+d*v,h=h*m+g*v,u=u*m+_*v,m===1-a){let E=1/Math.sqrt(l*l+c*c+h*h+u*u);l*=E,c*=E,h*=E,u*=E}}t[e]=l,t[e+1]=c,t[e+2]=h,t[e+3]=u}static multiplyQuaternionsFlat(t,e,n,i,r,o){let a=n[i],l=n[i+1],c=n[i+2],h=n[i+3],u=r[o],f=r[o+1],d=r[o+2],g=r[o+3];return t[e]=a*g+h*u+l*d-c*f,t[e+1]=l*g+h*f+c*u-a*d,t[e+2]=c*g+h*d+a*f-l*u,t[e+3]=h*g-a*u-l*f-c*d,t}get x(){return this._x}set x(t){this._x=t,this._onChangeCallback()}get y(){return this._y}set y(t){this._y=t,this._onChangeCallback()}get z(){return this._z}set z(t){this._z=t,this._onChangeCallback()}get w(){return this._w}set w(t){this._w=t,this._onChangeCallback()}set(t,e,n,i){return this._x=t,this._y=e,this._z=n,this._w=i,this._onChangeCallback(),this}clone(){return new this.constructor(this._x,this._y,this._z,this._w)}copy(t){return this._x=t.x,this._y=t.y,this._z=t.z,this._w=t.w,this._onChangeCallback(),this}setFromEuler(t,e=!0){let n=t._x,i=t._y,r=t._z,o=t._order,a=Math.cos,l=Math.sin,c=a(n/2),h=a(i/2),u=a(r/2),f=l(n/2),d=l(i/2),g=l(r/2);switch(o){case"XYZ":this._x=f*h*u+c*d*g,this._y=c*d*u-f*h*g,this._z=c*h*g+f*d*u,this._w=c*h*u-f*d*g;break;case"YXZ":this._x=f*h*u+c*d*g,this._y=c*d*u-f*h*g,this._z=c*h*g-f*d*u,this._w=c*h*u+f*d*g;break;case"ZXY":this._x=f*h*u-c*d*g,this._y=c*d*u+f*h*g,this._z=c*h*g+f*d*u,this._w=c*h*u-f*d*g;break;case"ZYX":this._x=f*h*u-c*d*g,this._y=c*d*u+f*h*g,this._z=c*h*g-f*d*u,this._w=c*h*u+f*d*g;break;case"YZX":this._x=f*h*u+c*d*g,this._y=c*d*u+f*h*g,this._z=c*h*g-f*d*u,this._w=c*h*u-f*d*g;break;case"XZY":this._x=f*h*u-c*d*g,this._y=c*d*u-f*h*g,this._z=c*h*g+f*d*u,this._w=c*h*u+f*d*g;break;default:console.warn("THREE.Quaternion: .setFromEuler() encountered an unknown order: "+o)}return e===!0&&this._onChangeCallback(),this}setFromAxisAngle(t,e){let n=e/2,i=Math.sin(n);return this._x=t.x*i,this._y=t.y*i,this._z=t.z*i,this._w=Math.cos(n),this._onChangeCallback(),this}setFromRotationMatrix(t){let e=t.elements,n=e[0],i=e[4],r=e[8],o=e[1],a=e[5],l=e[9],c=e[2],h=e[6],u=e[10],f=n+a+u;if(f>0){let d=.5/Math.sqrt(f+1);this._w=.25/d,this._x=(h-l)*d,this._y=(r-c)*d,this._z=(o-i)*d}else if(n>a&&n>u){let d=2*Math.sqrt(1+n-a-u);this._w=(h-l)/d,this._x=.25*d,this._y=(i+o)/d,this._z=(r+c)/d}else if(a>u){let d=2*Math.sqrt(1+a-n-u);this._w=(r-c)/d,this._x=(i+o)/d,this._y=.25*d,this._z=(l+h)/d}else{let d=2*Math.sqrt(1+u-n-a);this._w=(o-i)/d,this._x=(r+c)/d,this._y=(l+h)/d,this._z=.25*d}return this._onChangeCallback(),this}setFromUnitVectors(t,e){let n=t.dot(e)+1;return n<Number.EPSILON?(n=0,Math.abs(t.x)>Math.abs(t.z)?(this._x=-t.y,this._y=t.x,this._z=0,this._w=n):(this._x=0,this._y=-t.z,this._z=t.y,this._w=n)):(this._x=t.y*e.z-t.z*e.y,this._y=t.z*e.x-t.x*e.z,this._z=t.x*e.y-t.y*e.x,this._w=n),this.normalize()}angleTo(t){return 2*Math.acos(Math.abs(Sn(this.dot(t),-1,1)))}rotateTowards(t,e){let n=this.angleTo(t);if(n===0)return this;let i=Math.min(1,e/n);return this.slerp(t,i),this}identity(){return this.set(0,0,0,1)}invert(){return this.conjugate()}conjugate(){return this._x*=-1,this._y*=-1,this._z*=-1,this._onChangeCallback(),this}dot(t){return this._x*t._x+this._y*t._y+this._z*t._z+this._w*t._w}lengthSq(){return this._x*this._x+this._y*this._y+this._z*this._z+this._w*this._w}length(){return Math.sqrt(this._x*this._x+this._y*this._y+this._z*this._z+this._w*this._w)}normalize(){let t=this.length();return t===0?(this._x=0,this._y=0,this._z=0,this._w=1):(t=1/t,this._x=this._x*t,this._y=this._y*t,this._z=this._z*t,this._w=this._w*t),this._onChangeCallback(),this}multiply(t){return this.multiplyQuaternions(this,t)}premultiply(t){return this.multiplyQuaternions(t,this)}multiplyQuaternions(t,e){let n=t._x,i=t._y,r=t._z,o=t._w,a=e._x,l=e._y,c=e._z,h=e._w;return this._x=n*h+o*a+i*c-r*l,this._y=i*h+o*l+r*a-n*c,this._z=r*h+o*c+n*l-i*a,this._w=o*h-n*a-i*l-r*c,this._onChangeCallback(),this}slerp(t,e){if(e===0)return this;if(e===1)return this.copy(t);let n=this._x,i=this._y,r=this._z,o=this._w,a=o*t._w+n*t._x+i*t._y+r*t._z;if(a<0?(this._w=-t._w,this._x=-t._x,this._y=-t._y,this._z=-t._z,a=-a):this.copy(t),a>=1)return this._w=o,this._x=n,this._y=i,this._z=r,this;let l=1-a*a;if(l<=Number.EPSILON){let d=1-e;return this._w=d*o+e*this._w,this._x=d*n+e*this._x,this._y=d*i+e*this._y,this._z=d*r+e*this._z,this.normalize(),this}let c=Math.sqrt(l),h=Math.atan2(c,a),u=Math.sin((1-e)*h)/c,f=Math.sin(e*h)/c;return this._w=o*u+this._w*f,this._x=n*u+this._x*f,this._y=i*u+this._y*f,this._z=r*u+this._z*f,this._onChangeCallback(),this}slerpQuaternions(t,e,n){return this.copy(t).slerp(e,n)}random(){let t=2*Math.PI*Math.random(),e=2*Math.PI*Math.random(),n=Math.random(),i=Math.sqrt(1-n),r=Math.sqrt(n);return this.set(i*Math.sin(t),i*Math.cos(t),r*Math.sin(e),r*Math.cos(e))}equals(t){return t._x===this._x&&t._y===this._y&&t._z===this._z&&t._w===this._w}fromArray(t,e=0){return this._x=t[e],this._y=t[e+1],this._z=t[e+2],this._w=t[e+3],this._onChangeCallback(),this}toArray(t=[],e=0){return t[e]=this._x,t[e+1]=this._y,t[e+2]=this._z,t[e+3]=this._w,t}fromBufferAttribute(t,e){return this._x=t.getX(e),this._y=t.getY(e),this._z=t.getZ(e),this._w=t.getW(e),this._onChangeCallback(),this}toJSON(){return this.toArray()}_onChange(t){return this._onChangeCallback=t,this}_onChangeCallback(){}*[Symbol.iterator](){yield this._x,yield this._y,yield this._z,yield this._w}},B=class s{constructor(t=0,e=0,n=0){s.prototype.isVector3=!0,this.x=t,this.y=e,this.z=n}set(t,e,n){return n===void 0&&(n=this.z),this.x=t,this.y=e,this.z=n,this}setScalar(t){return this.x=t,this.y=t,this.z=t,this}setX(t){return this.x=t,this}setY(t){return this.y=t,this}setZ(t){return this.z=t,this}setComponent(t,e){switch(t){case 0:this.x=e;break;case 1:this.y=e;break;case 2:this.z=e;break;default:throw new Error("index is out of range: "+t)}return this}getComponent(t){switch(t){case 0:return this.x;case 1:return this.y;case 2:return this.z;default:throw new Error("index is out of range: "+t)}}clone(){return new this.constructor(this.x,this.y,this.z)}copy(t){return this.x=t.x,this.y=t.y,this.z=t.z,this}add(t){return this.x+=t.x,this.y+=t.y,this.z+=t.z,this}addScalar(t){return this.x+=t,this.y+=t,this.z+=t,this}addVectors(t,e){return this.x=t.x+e.x,this.y=t.y+e.y,this.z=t.z+e.z,this}addScaledVector(t,e){return this.x+=t.x*e,this.y+=t.y*e,this.z+=t.z*e,this}sub(t){return this.x-=t.x,this.y-=t.y,this.z-=t.z,this}subScalar(t){return this.x-=t,this.y-=t,this.z-=t,this}subVectors(t,e){return this.x=t.x-e.x,this.y=t.y-e.y,this.z=t.z-e.z,this}multiply(t){return this.x*=t.x,this.y*=t.y,this.z*=t.z,this}multiplyScalar(t){return this.x*=t,this.y*=t,this.z*=t,this}multiplyVectors(t,e){return this.x=t.x*e.x,this.y=t.y*e.y,this.z=t.z*e.z,this}applyEuler(t){return this.applyQuaternion(Ug.setFromEuler(t))}applyAxisAngle(t,e){return this.applyQuaternion(Ug.setFromAxisAngle(t,e))}applyMatrix3(t){let e=this.x,n=this.y,i=this.z,r=t.elements;return this.x=r[0]*e+r[3]*n+r[6]*i,this.y=r[1]*e+r[4]*n+r[7]*i,this.z=r[2]*e+r[5]*n+r[8]*i,this}applyNormalMatrix(t){return this.applyMatrix3(t).normalize()}applyMatrix4(t){let e=this.x,n=this.y,i=this.z,r=t.elements,o=1/(r[3]*e+r[7]*n+r[11]*i+r[15]);return this.x=(r[0]*e+r[4]*n+r[8]*i+r[12])*o,this.y=(r[1]*e+r[5]*n+r[9]*i+r[13])*o,this.z=(r[2]*e+r[6]*n+r[10]*i+r[14])*o,this}applyQuaternion(t){let e=this.x,n=this.y,i=this.z,r=t.x,o=t.y,a=t.z,l=t.w,c=2*(o*i-a*n),h=2*(a*e-r*i),u=2*(r*n-o*e);return this.x=e+l*c+o*u-a*h,this.y=n+l*h+a*c-r*u,this.z=i+l*u+r*h-o*c,this}project(t){return this.applyMatrix4(t.matrixWorldInverse).applyMatrix4(t.projectionMatrix)}unproject(t){return this.applyMatrix4(t.projectionMatrixInverse).applyMatrix4(t.matrixWorld)}transformDirection(t){let e=this.x,n=this.y,i=this.z,r=t.elements;return this.x=r[0]*e+r[4]*n+r[8]*i,this.y=r[1]*e+r[5]*n+r[9]*i,this.z=r[2]*e+r[6]*n+r[10]*i,this.normalize()}divide(t){return this.x/=t.x,this.y/=t.y,this.z/=t.z,this}divideScalar(t){return this.multiplyScalar(1/t)}min(t){return this.x=Math.min(this.x,t.x),this.y=Math.min(this.y,t.y),this.z=Math.min(this.z,t.z),this}max(t){return this.x=Math.max(this.x,t.x),this.y=Math.max(this.y,t.y),this.z=Math.max(this.z,t.z),this}clamp(t,e){return this.x=Math.max(t.x,Math.min(e.x,this.x)),this.y=Math.max(t.y,Math.min(e.y,this.y)),this.z=Math.max(t.z,Math.min(e.z,this.z)),this}clampScalar(t,e){return this.x=Math.max(t,Math.min(e,this.x)),this.y=Math.max(t,Math.min(e,this.y)),this.z=Math.max(t,Math.min(e,this.z)),this}clampLength(t,e){let n=this.length();return this.divideScalar(n||1).multiplyScalar(Math.max(t,Math.min(e,n)))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this.z=Math.floor(this.z),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this.z=Math.ceil(this.z),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this.z=Math.round(this.z),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this.z=Math.trunc(this.z),this}negate(){return this.x=-this.x,this.y=-this.y,this.z=-this.z,this}dot(t){return this.x*t.x+this.y*t.y+this.z*t.z}lengthSq(){return this.x*this.x+this.y*this.y+this.z*this.z}length(){return Math.sqrt(this.x*this.x+this.y*this.y+this.z*this.z)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)+Math.abs(this.z)}normalize(){return this.divideScalar(this.length()||1)}setLength(t){return this.normalize().multiplyScalar(t)}lerp(t,e){return this.x+=(t.x-this.x)*e,this.y+=(t.y-this.y)*e,this.z+=(t.z-this.z)*e,this}lerpVectors(t,e,n){return this.x=t.x+(e.x-t.x)*n,this.y=t.y+(e.y-t.y)*n,this.z=t.z+(e.z-t.z)*n,this}cross(t){return this.crossVectors(this,t)}crossVectors(t,e){let n=t.x,i=t.y,r=t.z,o=e.x,a=e.y,l=e.z;return this.x=i*l-r*a,this.y=r*o-n*l,this.z=n*a-i*o,this}projectOnVector(t){let e=t.lengthSq();if(e===0)return this.set(0,0,0);let n=t.dot(this)/e;return this.copy(t).multiplyScalar(n)}projectOnPlane(t){return Iu.copy(this).projectOnVector(t),this.sub(Iu)}reflect(t){return this.sub(Iu.copy(t).multiplyScalar(2*this.dot(t)))}angleTo(t){let e=Math.sqrt(this.lengthSq()*t.lengthSq());if(e===0)return Math.PI/2;let n=this.dot(t)/e;return Math.acos(Sn(n,-1,1))}distanceTo(t){return Math.sqrt(this.distanceToSquared(t))}distanceToSquared(t){let e=this.x-t.x,n=this.y-t.y,i=this.z-t.z;return e*e+n*n+i*i}manhattanDistanceTo(t){return Math.abs(this.x-t.x)+Math.abs(this.y-t.y)+Math.abs(this.z-t.z)}setFromSpherical(t){return this.setFromSphericalCoords(t.radius,t.phi,t.theta)}setFromSphericalCoords(t,e,n){let i=Math.sin(e)*t;return this.x=i*Math.sin(n),this.y=Math.cos(e)*t,this.z=i*Math.cos(n),this}setFromCylindrical(t){return this.setFromCylindricalCoords(t.radius,t.theta,t.y)}setFromCylindricalCoords(t,e,n){return this.x=t*Math.sin(e),this.y=n,this.z=t*Math.cos(e),this}setFromMatrixPosition(t){let e=t.elements;return this.x=e[12],this.y=e[13],this.z=e[14],this}setFromMatrixScale(t){let e=this.setFromMatrixColumn(t,0).length(),n=this.setFromMatrixColumn(t,1).length(),i=this.setFromMatrixColumn(t,2).length();return this.x=e,this.y=n,this.z=i,this}setFromMatrixColumn(t,e){return this.fromArray(t.elements,e*4)}setFromMatrix3Column(t,e){return this.fromArray(t.elements,e*3)}setFromEuler(t){return this.x=t._x,this.y=t._y,this.z=t._z,this}setFromColor(t){return this.x=t.r,this.y=t.g,this.z=t.b,this}equals(t){return t.x===this.x&&t.y===this.y&&t.z===this.z}fromArray(t,e=0){return this.x=t[e],this.y=t[e+1],this.z=t[e+2],this}toArray(t=[],e=0){return t[e]=this.x,t[e+1]=this.y,t[e+2]=this.z,t}fromBufferAttribute(t,e){return this.x=t.getX(e),this.y=t.getY(e),this.z=t.getZ(e),this}random(){return this.x=Math.random(),this.y=Math.random(),this.z=Math.random(),this}randomDirection(){let t=Math.random()*Math.PI*2,e=Math.random()*2-1,n=Math.sqrt(1-e*e);return this.x=n*Math.cos(t),this.y=e,this.z=n*Math.sin(t),this}*[Symbol.iterator](){yield this.x,yield this.y,yield this.z}},Iu=new B,Ug=new wi,as=class{constructor(t=new B(1/0,1/0,1/0),e=new B(-1/0,-1/0,-1/0)){this.isBox3=!0,this.min=t,this.max=e}set(t,e){return this.min.copy(t),this.max.copy(e),this}setFromArray(t){this.makeEmpty();for(let e=0,n=t.length;e<n;e+=3)this.expandByPoint(yi.fromArray(t,e));return this}setFromBufferAttribute(t){this.makeEmpty();for(let e=0,n=t.count;e<n;e++)this.expandByPoint(yi.fromBufferAttribute(t,e));return this}setFromPoints(t){this.makeEmpty();for(let e=0,n=t.length;e<n;e++)this.expandByPoint(t[e]);return this}setFromCenterAndSize(t,e){let n=yi.copy(e).multiplyScalar(.5);return this.min.copy(t).sub(n),this.max.copy(t).add(n),this}setFromObject(t,e=!1){return this.makeEmpty(),this.expandByObject(t,e)}clone(){return new this.constructor().copy(this)}copy(t){return this.min.copy(t.min),this.max.copy(t.max),this}makeEmpty(){return this.min.x=this.min.y=this.min.z=1/0,this.max.x=this.max.y=this.max.z=-1/0,this}isEmpty(){return this.max.x<this.min.x||this.max.y<this.min.y||this.max.z<this.min.z}getCenter(t){return this.isEmpty()?t.set(0,0,0):t.addVectors(this.min,this.max).multiplyScalar(.5)}getSize(t){return this.isEmpty()?t.set(0,0,0):t.subVectors(this.max,this.min)}expandByPoint(t){return this.min.min(t),this.max.max(t),this}expandByVector(t){return this.min.sub(t),this.max.add(t),this}expandByScalar(t){return this.min.addScalar(-t),this.max.addScalar(t),this}expandByObject(t,e=!1){t.updateWorldMatrix(!1,!1);let n=t.geometry;if(n!==void 0){let r=n.getAttribute("position");if(e===!0&&r!==void 0&&t.isInstancedMesh!==!0)for(let o=0,a=r.count;o<a;o++)t.isMesh===!0?t.getVertexPosition(o,yi):yi.fromBufferAttribute(r,o),yi.applyMatrix4(t.matrixWorld),this.expandByPoint(yi);else t.boundingBox!==void 0?(t.boundingBox===null&&t.computeBoundingBox(),Xl.copy(t.boundingBox)):(n.boundingBox===null&&n.computeBoundingBox(),Xl.copy(n.boundingBox)),Xl.applyMatrix4(t.matrixWorld),this.union(Xl)}let i=t.children;for(let r=0,o=i.length;r<o;r++)this.expandByObject(i[r],e);return this}containsPoint(t){return t.x>=this.min.x&&t.x<=this.max.x&&t.y>=this.min.y&&t.y<=this.max.y&&t.z>=this.min.z&&t.z<=this.max.z}containsBox(t){return this.min.x<=t.min.x&&t.max.x<=this.max.x&&this.min.y<=t.min.y&&t.max.y<=this.max.y&&this.min.z<=t.min.z&&t.max.z<=this.max.z}getParameter(t,e){return e.set((t.x-this.min.x)/(this.max.x-this.min.x),(t.y-this.min.y)/(this.max.y-this.min.y),(t.z-this.min.z)/(this.max.z-this.min.z))}intersectsBox(t){return t.max.x>=this.min.x&&t.min.x<=this.max.x&&t.max.y>=this.min.y&&t.min.y<=this.max.y&&t.max.z>=this.min.z&&t.min.z<=this.max.z}intersectsSphere(t){return this.clampPoint(t.center,yi),yi.distanceToSquared(t.center)<=t.radius*t.radius}intersectsPlane(t){let e,n;return t.normal.x>0?(e=t.normal.x*this.min.x,n=t.normal.x*this.max.x):(e=t.normal.x*this.max.x,n=t.normal.x*this.min.x),t.normal.y>0?(e+=t.normal.y*this.min.y,n+=t.normal.y*this.max.y):(e+=t.normal.y*this.max.y,n+=t.normal.y*this.min.y),t.normal.z>0?(e+=t.normal.z*this.min.z,n+=t.normal.z*this.max.z):(e+=t.normal.z*this.max.z,n+=t.normal.z*this.min.z),e<=-t.constant&&n>=-t.constant}intersectsTriangle(t){if(this.isEmpty())return!1;this.getCenter(Ca),Yl.subVectors(this.max,Ca),so.subVectors(t.a,Ca),ro.subVectors(t.b,Ca),oo.subVectors(t.c,Ca),Cs.subVectors(ro,so),Rs.subVectors(oo,ro),cr.subVectors(so,oo);let e=[0,-Cs.z,Cs.y,0,-Rs.z,Rs.y,0,-cr.z,cr.y,Cs.z,0,-Cs.x,Rs.z,0,-Rs.x,cr.z,0,-cr.x,-Cs.y,Cs.x,0,-Rs.y,Rs.x,0,-cr.y,cr.x,0];return!Lu(e,so,ro,oo,Yl)||(e=[1,0,0,0,1,0,0,0,1],!Lu(e,so,ro,oo,Yl))?!1:(ql.crossVectors(Cs,Rs),e=[ql.x,ql.y,ql.z],Lu(e,so,ro,oo,Yl))}clampPoint(t,e){return e.copy(t).clamp(this.min,this.max)}distanceToPoint(t){return this.clampPoint(t,yi).distanceTo(t)}getBoundingSphere(t){return this.isEmpty()?t.makeEmpty():(this.getCenter(t.center),t.radius=this.getSize(yi).length()*.5),t}intersect(t){return this.min.max(t.min),this.max.min(t.max),this.isEmpty()&&this.makeEmpty(),this}union(t){return this.min.min(t.min),this.max.max(t.max),this}applyMatrix4(t){return this.isEmpty()?this:(Ki[0].set(this.min.x,this.min.y,this.min.z).applyMatrix4(t),Ki[1].set(this.min.x,this.min.y,this.max.z).applyMatrix4(t),Ki[2].set(this.min.x,this.max.y,this.min.z).applyMatrix4(t),Ki[3].set(this.min.x,this.max.y,this.max.z).applyMatrix4(t),Ki[4].set(this.max.x,this.min.y,this.min.z).applyMatrix4(t),Ki[5].set(this.max.x,this.min.y,this.max.z).applyMatrix4(t),Ki[6].set(this.max.x,this.max.y,this.min.z).applyMatrix4(t),Ki[7].set(this.max.x,this.max.y,this.max.z).applyMatrix4(t),this.setFromPoints(Ki),this)}translate(t){return this.min.add(t),this.max.add(t),this}equals(t){return t.min.equals(this.min)&&t.max.equals(this.max)}},Ki=[new B,new B,new B,new B,new B,new B,new B,new B],yi=new B,Xl=new as,so=new B,ro=new B,oo=new B,Cs=new B,Rs=new B,cr=new B,Ca=new B,Yl=new B,ql=new B,hr=new B;function Lu(s,t,e,n,i){for(let r=0,o=s.length-3;r<=o;r+=3){hr.fromArray(s,r);let a=i.x*Math.abs(hr.x)+i.y*Math.abs(hr.y)+i.z*Math.abs(hr.z),l=t.dot(hr),c=e.dot(hr),h=n.dot(hr);if(Math.max(-Math.max(l,c,h),Math.min(l,c,h))>a)return!1}return!0}var xy=new as,Ra=new B,Du=new B,Sr=class{constructor(t=new B,e=-1){this.isSphere=!0,this.center=t,this.radius=e}set(t,e){return this.center.copy(t),this.radius=e,this}setFromPoints(t,e){let n=this.center;e!==void 0?n.copy(e):xy.setFromPoints(t).getCenter(n);let i=0;for(let r=0,o=t.length;r<o;r++)i=Math.max(i,n.distanceToSquared(t[r]));return this.radius=Math.sqrt(i),this}copy(t){return this.center.copy(t.center),this.radius=t.radius,this}isEmpty(){return this.radius<0}makeEmpty(){return this.center.set(0,0,0),this.radius=-1,this}containsPoint(t){return t.distanceToSquared(this.center)<=this.radius*this.radius}distanceToPoint(t){return t.distanceTo(this.center)-this.radius}intersectsSphere(t){let e=this.radius+t.radius;return t.center.distanceToSquared(this.center)<=e*e}intersectsBox(t){return t.intersectsSphere(this)}intersectsPlane(t){return Math.abs(t.distanceToPoint(this.center))<=this.radius}clampPoint(t,e){let n=this.center.distanceToSquared(t);return e.copy(t),n>this.radius*this.radius&&(e.sub(this.center).normalize(),e.multiplyScalar(this.radius).add(this.center)),e}getBoundingBox(t){return this.isEmpty()?(t.makeEmpty(),t):(t.set(this.center,this.center),t.expandByScalar(this.radius),t)}applyMatrix4(t){return this.center.applyMatrix4(t),this.radius=this.radius*t.getMaxScaleOnAxis(),this}translate(t){return this.center.add(t),this}expandByPoint(t){if(this.isEmpty())return this.center.copy(t),this.radius=0,this;Ra.subVectors(t,this.center);let e=Ra.lengthSq();if(e>this.radius*this.radius){let n=Math.sqrt(e),i=(n-this.radius)*.5;this.center.addScaledVector(Ra,i/n),this.radius+=i}return this}union(t){return t.isEmpty()?this:this.isEmpty()?(this.copy(t),this):(this.center.equals(t.center)===!0?this.radius=Math.max(this.radius,t.radius):(Du.subVectors(t.center,this.center).setLength(t.radius),this.expandByPoint(Ra.copy(t.center).add(Du)),this.expandByPoint(Ra.copy(t.center).sub(Du))),this)}equals(t){return t.center.equals(this.center)&&t.radius===this.radius}clone(){return new this.constructor().copy(this)}},Qi=new B,Uu=new B,Zl=new B,Ps=new B,Nu=new B,$l=new B,Ou=new B,Kf=class{constructor(t=new B,e=new B(0,0,-1)){this.origin=t,this.direction=e}set(t,e){return this.origin.copy(t),this.direction.copy(e),this}copy(t){return this.origin.copy(t.origin),this.direction.copy(t.direction),this}at(t,e){return e.copy(this.origin).addScaledVector(this.direction,t)}lookAt(t){return this.direction.copy(t).sub(this.origin).normalize(),this}recast(t){return this.origin.copy(this.at(t,Qi)),this}closestPointToPoint(t,e){e.subVectors(t,this.origin);let n=e.dot(this.direction);return n<0?e.copy(this.origin):e.copy(this.origin).addScaledVector(this.direction,n)}distanceToPoint(t){return Math.sqrt(this.distanceSqToPoint(t))}distanceSqToPoint(t){let e=Qi.subVectors(t,this.origin).dot(this.direction);return e<0?this.origin.distanceToSquared(t):(Qi.copy(this.origin).addScaledVector(this.direction,e),Qi.distanceToSquared(t))}distanceSqToSegment(t,e,n,i){Uu.copy(t).add(e).multiplyScalar(.5),Zl.copy(e).sub(t).normalize(),Ps.copy(this.origin).sub(Uu);let r=t.distanceTo(e)*.5,o=-this.direction.dot(Zl),a=Ps.dot(this.direction),l=-Ps.dot(Zl),c=Ps.lengthSq(),h=Math.abs(1-o*o),u,f,d,g;if(h>0)if(u=o*l-a,f=o*a-l,g=r*h,u>=0)if(f>=-g)if(f<=g){let _=1/h;u*=_,f*=_,d=u*(u+o*f+2*a)+f*(o*u+f+2*l)+c}else f=r,u=Math.max(0,-(o*f+a)),d=-u*u+f*(f+2*l)+c;else f=-r,u=Math.max(0,-(o*f+a)),d=-u*u+f*(f+2*l)+c;else f<=-g?(u=Math.max(0,-(-o*r+a)),f=u>0?-r:Math.min(Math.max(-r,-l),r),d=-u*u+f*(f+2*l)+c):f<=g?(u=0,f=Math.min(Math.max(-r,-l),r),d=f*(f+2*l)+c):(u=Math.max(0,-(o*r+a)),f=u>0?r:Math.min(Math.max(-r,-l),r),d=-u*u+f*(f+2*l)+c);else f=o>0?-r:r,u=Math.max(0,-(o*f+a)),d=-u*u+f*(f+2*l)+c;return n&&n.copy(this.origin).addScaledVector(this.direction,u),i&&i.copy(Uu).addScaledVector(Zl,f),d}intersectSphere(t,e){Qi.subVectors(t.center,this.origin);let n=Qi.dot(this.direction),i=Qi.dot(Qi)-n*n,r=t.radius*t.radius;if(i>r)return null;let o=Math.sqrt(r-i),a=n-o,l=n+o;return l<0?null:a<0?this.at(l,e):this.at(a,e)}intersectsSphere(t){return this.distanceSqToPoint(t.center)<=t.radius*t.radius}distanceToPlane(t){let e=t.normal.dot(this.direction);if(e===0)return t.distanceToPoint(this.origin)===0?0:null;let n=-(this.origin.dot(t.normal)+t.constant)/e;return n>=0?n:null}intersectPlane(t,e){let n=this.distanceToPlane(t);return n===null?null:this.at(n,e)}intersectsPlane(t){let e=t.distanceToPoint(this.origin);return e===0||t.normal.dot(this.direction)*e<0}intersectBox(t,e){let n,i,r,o,a,l,c=1/this.direction.x,h=1/this.direction.y,u=1/this.direction.z,f=this.origin;return c>=0?(n=(t.min.x-f.x)*c,i=(t.max.x-f.x)*c):(n=(t.max.x-f.x)*c,i=(t.min.x-f.x)*c),h>=0?(r=(t.min.y-f.y)*h,o=(t.max.y-f.y)*h):(r=(t.max.y-f.y)*h,o=(t.min.y-f.y)*h),n>o||r>i||((r>n||isNaN(n))&&(n=r),(o<i||isNaN(i))&&(i=o),u>=0?(a=(t.min.z-f.z)*u,l=(t.max.z-f.z)*u):(a=(t.max.z-f.z)*u,l=(t.min.z-f.z)*u),n>l||a>i)||((a>n||n!==n)&&(n=a),(l<i||i!==i)&&(i=l),i<0)?null:this.at(n>=0?n:i,e)}intersectsBox(t){return this.intersectBox(t,Qi)!==null}intersectTriangle(t,e,n,i,r){Nu.subVectors(e,t),$l.subVectors(n,t),Ou.crossVectors(Nu,$l);let o=this.direction.dot(Ou),a;if(o>0){if(i)return null;a=1}else if(o<0)a=-1,o=-o;else return null;Ps.subVectors(this.origin,t);let l=a*this.direction.dot($l.crossVectors(Ps,$l));if(l<0)return null;let c=a*this.direction.dot(Nu.cross(Ps));if(c<0||l+c>o)return null;let h=-a*Ps.dot(Ou);return h<0?null:this.at(h/o,r)}applyMatrix4(t){return this.origin.applyMatrix4(t),this.direction.transformDirection(t),this}equals(t){return t.origin.equals(this.origin)&&t.direction.equals(this.direction)}clone(){return new this.constructor().copy(this)}},Ce=class s{constructor(t,e,n,i,r,o,a,l,c,h,u,f,d,g,_,m){s.prototype.isMatrix4=!0,this.elements=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1],t!==void 0&&this.set(t,e,n,i,r,o,a,l,c,h,u,f,d,g,_,m)}set(t,e,n,i,r,o,a,l,c,h,u,f,d,g,_,m){let p=this.elements;return p[0]=t,p[4]=e,p[8]=n,p[12]=i,p[1]=r,p[5]=o,p[9]=a,p[13]=l,p[2]=c,p[6]=h,p[10]=u,p[14]=f,p[3]=d,p[7]=g,p[11]=_,p[15]=m,this}identity(){return this.set(1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1),this}clone(){return new s().fromArray(this.elements)}copy(t){let e=this.elements,n=t.elements;return e[0]=n[0],e[1]=n[1],e[2]=n[2],e[3]=n[3],e[4]=n[4],e[5]=n[5],e[6]=n[6],e[7]=n[7],e[8]=n[8],e[9]=n[9],e[10]=n[10],e[11]=n[11],e[12]=n[12],e[13]=n[13],e[14]=n[14],e[15]=n[15],this}copyPosition(t){let e=this.elements,n=t.elements;return e[12]=n[12],e[13]=n[13],e[14]=n[14],this}setFromMatrix3(t){let e=t.elements;return this.set(e[0],e[3],e[6],0,e[1],e[4],e[7],0,e[2],e[5],e[8],0,0,0,0,1),this}extractBasis(t,e,n){return t.setFromMatrixColumn(this,0),e.setFromMatrixColumn(this,1),n.setFromMatrixColumn(this,2),this}makeBasis(t,e,n){return this.set(t.x,e.x,n.x,0,t.y,e.y,n.y,0,t.z,e.z,n.z,0,0,0,0,1),this}extractRotation(t){let e=this.elements,n=t.elements,i=1/ao.setFromMatrixColumn(t,0).length(),r=1/ao.setFromMatrixColumn(t,1).length(),o=1/ao.setFromMatrixColumn(t,2).length();return e[0]=n[0]*i,e[1]=n[1]*i,e[2]=n[2]*i,e[3]=0,e[4]=n[4]*r,e[5]=n[5]*r,e[6]=n[6]*r,e[7]=0,e[8]=n[8]*o,e[9]=n[9]*o,e[10]=n[10]*o,e[11]=0,e[12]=0,e[13]=0,e[14]=0,e[15]=1,this}makeRotationFromEuler(t){let e=this.elements,n=t.x,i=t.y,r=t.z,o=Math.cos(n),a=Math.sin(n),l=Math.cos(i),c=Math.sin(i),h=Math.cos(r),u=Math.sin(r);if(t.order==="XYZ"){let f=o*h,d=o*u,g=a*h,_=a*u;e[0]=l*h,e[4]=-l*u,e[8]=c,e[1]=d+g*c,e[5]=f-_*c,e[9]=-a*l,e[2]=_-f*c,e[6]=g+d*c,e[10]=o*l}else if(t.order==="YXZ"){let f=l*h,d=l*u,g=c*h,_=c*u;e[0]=f+_*a,e[4]=g*a-d,e[8]=o*c,e[1]=o*u,e[5]=o*h,e[9]=-a,e[2]=d*a-g,e[6]=_+f*a,e[10]=o*l}else if(t.order==="ZXY"){let f=l*h,d=l*u,g=c*h,_=c*u;e[0]=f-_*a,e[4]=-o*u,e[8]=g+d*a,e[1]=d+g*a,e[5]=o*h,e[9]=_-f*a,e[2]=-o*c,e[6]=a,e[10]=o*l}else if(t.order==="ZYX"){let f=o*h,d=o*u,g=a*h,_=a*u;e[0]=l*h,e[4]=g*c-d,e[8]=f*c+_,e[1]=l*u,e[5]=_*c+f,e[9]=d*c-g,e[2]=-c,e[6]=a*l,e[10]=o*l}else if(t.order==="YZX"){let f=o*l,d=o*c,g=a*l,_=a*c;e[0]=l*h,e[4]=_-f*u,e[8]=g*u+d,e[1]=u,e[5]=o*h,e[9]=-a*h,e[2]=-c*h,e[6]=d*u+g,e[10]=f-_*u}else if(t.order==="XZY"){let f=o*l,d=o*c,g=a*l,_=a*c;e[0]=l*h,e[4]=-u,e[8]=c*h,e[1]=f*u+_,e[5]=o*h,e[9]=d*u-g,e[2]=g*u-d,e[6]=a*h,e[10]=_*u+f}return e[3]=0,e[7]=0,e[11]=0,e[12]=0,e[13]=0,e[14]=0,e[15]=1,this}makeRotationFromQuaternion(t){return this.compose(yy,t,My)}lookAt(t,e,n){let i=this.elements;return Kn.subVectors(t,e),Kn.lengthSq()===0&&(Kn.z=1),Kn.normalize(),Is.crossVectors(n,Kn),Is.lengthSq()===0&&(Math.abs(n.z)===1?Kn.x+=1e-4:Kn.z+=1e-4,Kn.normalize(),Is.crossVectors(n,Kn)),Is.normalize(),Jl.crossVectors(Kn,Is),i[0]=Is.x,i[4]=Jl.x,i[8]=Kn.x,i[1]=Is.y,i[5]=Jl.y,i[9]=Kn.y,i[2]=Is.z,i[6]=Jl.z,i[10]=Kn.z,this}multiply(t){return this.multiplyMatrices(this,t)}premultiply(t){return this.multiplyMatrices(t,this)}multiplyMatrices(t,e){let n=t.elements,i=e.elements,r=this.elements,o=n[0],a=n[4],l=n[8],c=n[12],h=n[1],u=n[5],f=n[9],d=n[13],g=n[2],_=n[6],m=n[10],p=n[14],S=n[3],y=n[7],v=n[11],E=n[15],A=i[0],T=i[4],R=i[8],M=i[12],x=i[1],L=i[5],U=i[9],F=i[13],z=i[2],q=i[6],H=i[10],W=i[14],V=i[3],st=i[7],I=i[11],at=i[15];return r[0]=o*A+a*x+l*z+c*V,r[4]=o*T+a*L+l*q+c*st,r[8]=o*R+a*U+l*H+c*I,r[12]=o*M+a*F+l*W+c*at,r[1]=h*A+u*x+f*z+d*V,r[5]=h*T+u*L+f*q+d*st,r[9]=h*R+u*U+f*H+d*I,r[13]=h*M+u*F+f*W+d*at,r[2]=g*A+_*x+m*z+p*V,r[6]=g*T+_*L+m*q+p*st,r[10]=g*R+_*U+m*H+p*I,r[14]=g*M+_*F+m*W+p*at,r[3]=S*A+y*x+v*z+E*V,r[7]=S*T+y*L+v*q+E*st,r[11]=S*R+y*U+v*H+E*I,r[15]=S*M+y*F+v*W+E*at,this}multiplyScalar(t){let e=this.elements;return e[0]*=t,e[4]*=t,e[8]*=t,e[12]*=t,e[1]*=t,e[5]*=t,e[9]*=t,e[13]*=t,e[2]*=t,e[6]*=t,e[10]*=t,e[14]*=t,e[3]*=t,e[7]*=t,e[11]*=t,e[15]*=t,this}determinant(){let t=this.elements,e=t[0],n=t[4],i=t[8],r=t[12],o=t[1],a=t[5],l=t[9],c=t[13],h=t[2],u=t[6],f=t[10],d=t[14],g=t[3],_=t[7],m=t[11],p=t[15];return g*(+r*l*u-i*c*u-r*a*f+n*c*f+i*a*d-n*l*d)+_*(+e*l*d-e*c*f+r*o*f-i*o*d+i*c*h-r*l*h)+m*(+e*c*u-e*a*d-r*o*u+n*o*d+r*a*h-n*c*h)+p*(-i*a*h-e*l*u+e*a*f+i*o*u-n*o*f+n*l*h)}transpose(){let t=this.elements,e;return e=t[1],t[1]=t[4],t[4]=e,e=t[2],t[2]=t[8],t[8]=e,e=t[6],t[6]=t[9],t[9]=e,e=t[3],t[3]=t[12],t[12]=e,e=t[7],t[7]=t[13],t[13]=e,e=t[11],t[11]=t[14],t[14]=e,this}setPosition(t,e,n){let i=this.elements;return t.isVector3?(i[12]=t.x,i[13]=t.y,i[14]=t.z):(i[12]=t,i[13]=e,i[14]=n),this}invert(){let t=this.elements,e=t[0],n=t[1],i=t[2],r=t[3],o=t[4],a=t[5],l=t[6],c=t[7],h=t[8],u=t[9],f=t[10],d=t[11],g=t[12],_=t[13],m=t[14],p=t[15],S=u*m*c-_*f*c+_*l*d-a*m*d-u*l*p+a*f*p,y=g*f*c-h*m*c-g*l*d+o*m*d+h*l*p-o*f*p,v=h*_*c-g*u*c+g*a*d-o*_*d-h*a*p+o*u*p,E=g*u*l-h*_*l-g*a*f+o*_*f+h*a*m-o*u*m,A=e*S+n*y+i*v+r*E;if(A===0)return this.set(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0);let T=1/A;return t[0]=S*T,t[1]=(_*f*r-u*m*r-_*i*d+n*m*d+u*i*p-n*f*p)*T,t[2]=(a*m*r-_*l*r+_*i*c-n*m*c-a*i*p+n*l*p)*T,t[3]=(u*l*r-a*f*r-u*i*c+n*f*c+a*i*d-n*l*d)*T,t[4]=y*T,t[5]=(h*m*r-g*f*r+g*i*d-e*m*d-h*i*p+e*f*p)*T,t[6]=(g*l*r-o*m*r-g*i*c+e*m*c+o*i*p-e*l*p)*T,t[7]=(o*f*r-h*l*r+h*i*c-e*f*c-o*i*d+e*l*d)*T,t[8]=v*T,t[9]=(g*u*r-h*_*r-g*n*d+e*_*d+h*n*p-e*u*p)*T,t[10]=(o*_*r-g*a*r+g*n*c-e*_*c-o*n*p+e*a*p)*T,t[11]=(h*a*r-o*u*r-h*n*c+e*u*c+o*n*d-e*a*d)*T,t[12]=E*T,t[13]=(h*_*i-g*u*i+g*n*f-e*_*f-h*n*m+e*u*m)*T,t[14]=(g*a*i-o*_*i-g*n*l+e*_*l+o*n*m-e*a*m)*T,t[15]=(o*u*i-h*a*i+h*n*l-e*u*l-o*n*f+e*a*f)*T,this}scale(t){let e=this.elements,n=t.x,i=t.y,r=t.z;return e[0]*=n,e[4]*=i,e[8]*=r,e[1]*=n,e[5]*=i,e[9]*=r,e[2]*=n,e[6]*=i,e[10]*=r,e[3]*=n,e[7]*=i,e[11]*=r,this}getMaxScaleOnAxis(){let t=this.elements,e=t[0]*t[0]+t[1]*t[1]+t[2]*t[2],n=t[4]*t[4]+t[5]*t[5]+t[6]*t[6],i=t[8]*t[8]+t[9]*t[9]+t[10]*t[10];return Math.sqrt(Math.max(e,n,i))}makeTranslation(t,e,n){return t.isVector3?this.set(1,0,0,t.x,0,1,0,t.y,0,0,1,t.z,0,0,0,1):this.set(1,0,0,t,0,1,0,e,0,0,1,n,0,0,0,1),this}makeRotationX(t){let e=Math.cos(t),n=Math.sin(t);return this.set(1,0,0,0,0,e,-n,0,0,n,e,0,0,0,0,1),this}makeRotationY(t){let e=Math.cos(t),n=Math.sin(t);return this.set(e,0,n,0,0,1,0,0,-n,0,e,0,0,0,0,1),this}makeRotationZ(t){let e=Math.cos(t),n=Math.sin(t);return this.set(e,-n,0,0,n,e,0,0,0,0,1,0,0,0,0,1),this}makeRotationAxis(t,e){let n=Math.cos(e),i=Math.sin(e),r=1-n,o=t.x,a=t.y,l=t.z,c=r*o,h=r*a;return this.set(c*o+n,c*a-i*l,c*l+i*a,0,c*a+i*l,h*a+n,h*l-i*o,0,c*l-i*a,h*l+i*o,r*l*l+n,0,0,0,0,1),this}makeScale(t,e,n){return this.set(t,0,0,0,0,e,0,0,0,0,n,0,0,0,0,1),this}makeShear(t,e,n,i,r,o){return this.set(1,n,r,0,t,1,o,0,e,i,1,0,0,0,0,1),this}compose(t,e,n){let i=this.elements,r=e._x,o=e._y,a=e._z,l=e._w,c=r+r,h=o+o,u=a+a,f=r*c,d=r*h,g=r*u,_=o*h,m=o*u,p=a*u,S=l*c,y=l*h,v=l*u,E=n.x,A=n.y,T=n.z;return i[0]=(1-(_+p))*E,i[1]=(d+v)*E,i[2]=(g-y)*E,i[3]=0,i[4]=(d-v)*A,i[5]=(1-(f+p))*A,i[6]=(m+S)*A,i[7]=0,i[8]=(g+y)*T,i[9]=(m-S)*T,i[10]=(1-(f+_))*T,i[11]=0,i[12]=t.x,i[13]=t.y,i[14]=t.z,i[15]=1,this}decompose(t,e,n){let i=this.elements,r=ao.set(i[0],i[1],i[2]).length(),o=ao.set(i[4],i[5],i[6]).length(),a=ao.set(i[8],i[9],i[10]).length();this.determinant()<0&&(r=-r),t.x=i[12],t.y=i[13],t.z=i[14],Mi.copy(this);let c=1/r,h=1/o,u=1/a;return Mi.elements[0]*=c,Mi.elements[1]*=c,Mi.elements[2]*=c,Mi.elements[4]*=h,Mi.elements[5]*=h,Mi.elements[6]*=h,Mi.elements[8]*=u,Mi.elements[9]*=u,Mi.elements[10]*=u,e.setFromRotationMatrix(Mi),n.x=r,n.y=o,n.z=a,this}makePerspective(t,e,n,i,r,o,a=ss){let l=this.elements,c=2*r/(e-t),h=2*r/(n-i),u=(e+t)/(e-t),f=(n+i)/(n-i),d,g;if(a===ss)d=-(o+r)/(o-r),g=-2*o*r/(o-r);else if(a===bc)d=-o/(o-r),g=-o*r/(o-r);else throw new Error("THREE.Matrix4.makePerspective(): Invalid coordinate system: "+a);return l[0]=c,l[4]=0,l[8]=u,l[12]=0,l[1]=0,l[5]=h,l[9]=f,l[13]=0,l[2]=0,l[6]=0,l[10]=d,l[14]=g,l[3]=0,l[7]=0,l[11]=-1,l[15]=0,this}makeOrthographic(t,e,n,i,r,o,a=ss){let l=this.elements,c=1/(e-t),h=1/(n-i),u=1/(o-r),f=(e+t)*c,d=(n+i)*h,g,_;if(a===ss)g=(o+r)*u,_=-2*u;else if(a===bc)g=r*u,_=-1*u;else throw new Error("THREE.Matrix4.makeOrthographic(): Invalid coordinate system: "+a);return l[0]=2*c,l[4]=0,l[8]=0,l[12]=-f,l[1]=0,l[5]=2*h,l[9]=0,l[13]=-d,l[2]=0,l[6]=0,l[10]=_,l[14]=-g,l[3]=0,l[7]=0,l[11]=0,l[15]=1,this}equals(t){let e=this.elements,n=t.elements;for(let i=0;i<16;i++)if(e[i]!==n[i])return!1;return!0}fromArray(t,e=0){for(let n=0;n<16;n++)this.elements[n]=t[n+e];return this}toArray(t=[],e=0){let n=this.elements;return t[e]=n[0],t[e+1]=n[1],t[e+2]=n[2],t[e+3]=n[3],t[e+4]=n[4],t[e+5]=n[5],t[e+6]=n[6],t[e+7]=n[7],t[e+8]=n[8],t[e+9]=n[9],t[e+10]=n[10],t[e+11]=n[11],t[e+12]=n[12],t[e+13]=n[13],t[e+14]=n[14],t[e+15]=n[15],t}},ao=new B,Mi=new Ce,yy=new B(0,0,0),My=new B(1,1,1),Is=new B,Jl=new B,Kn=new B,Ng=new Ce,Og=new wi,mi=class s{constructor(t=0,e=0,n=0,i=s.DEFAULT_ORDER){this.isEuler=!0,this._x=t,this._y=e,this._z=n,this._order=i}get x(){return this._x}set x(t){this._x=t,this._onChangeCallback()}get y(){return this._y}set y(t){this._y=t,this._onChangeCallback()}get z(){return this._z}set z(t){this._z=t,this._onChangeCallback()}get order(){return this._order}set order(t){this._order=t,this._onChangeCallback()}set(t,e,n,i=this._order){return this._x=t,this._y=e,this._z=n,this._order=i,this._onChangeCallback(),this}clone(){return new this.constructor(this._x,this._y,this._z,this._order)}copy(t){return this._x=t._x,this._y=t._y,this._z=t._z,this._order=t._order,this._onChangeCallback(),this}setFromRotationMatrix(t,e=this._order,n=!0){let i=t.elements,r=i[0],o=i[4],a=i[8],l=i[1],c=i[5],h=i[9],u=i[2],f=i[6],d=i[10];switch(e){case"XYZ":this._y=Math.asin(Sn(a,-1,1)),Math.abs(a)<.9999999?(this._x=Math.atan2(-h,d),this._z=Math.atan2(-o,r)):(this._x=Math.atan2(f,c),this._z=0);break;case"YXZ":this._x=Math.asin(-Sn(h,-1,1)),Math.abs(h)<.9999999?(this._y=Math.atan2(a,d),this._z=Math.atan2(l,c)):(this._y=Math.atan2(-u,r),this._z=0);break;case"ZXY":this._x=Math.asin(Sn(f,-1,1)),Math.abs(f)<.9999999?(this._y=Math.atan2(-u,d),this._z=Math.atan2(-o,c)):(this._y=0,this._z=Math.atan2(l,r));break;case"ZYX":this._y=Math.asin(-Sn(u,-1,1)),Math.abs(u)<.9999999?(this._x=Math.atan2(f,d),this._z=Math.atan2(l,r)):(this._x=0,this._z=Math.atan2(-o,c));break;case"YZX":this._z=Math.asin(Sn(l,-1,1)),Math.abs(l)<.9999999?(this._x=Math.atan2(-h,c),this._y=Math.atan2(-u,r)):(this._x=0,this._y=Math.atan2(a,d));break;case"XZY":this._z=Math.asin(-Sn(o,-1,1)),Math.abs(o)<.9999999?(this._x=Math.atan2(f,c),this._y=Math.atan2(a,r)):(this._x=Math.atan2(-h,d),this._y=0);break;default:console.warn("THREE.Euler: .setFromRotationMatrix() encountered an unknown order: "+e)}return this._order=e,n===!0&&this._onChangeCallback(),this}setFromQuaternion(t,e,n){return Ng.makeRotationFromQuaternion(t),this.setFromRotationMatrix(Ng,e,n)}setFromVector3(t,e=this._order){return this.set(t.x,t.y,t.z,e)}reorder(t){return Og.setFromEuler(this),this.setFromQuaternion(Og,t)}equals(t){return t._x===this._x&&t._y===this._y&&t._z===this._z&&t._order===this._order}fromArray(t){return this._x=t[0],this._y=t[1],this._z=t[2],t[3]!==void 0&&(this._order=t[3]),this._onChangeCallback(),this}toArray(t=[],e=0){return t[e]=this._x,t[e+1]=this._y,t[e+2]=this._z,t[e+3]=this._order,t}_onChange(t){return this._onChangeCallback=t,this}_onChangeCallback(){}*[Symbol.iterator](){yield this._x,yield this._y,yield this._z,yield this._order}};mi.DEFAULT_ORDER="XYZ";var Ac=class{constructor(){this.mask=1}set(t){this.mask=(1<<t|0)>>>0}enable(t){this.mask|=1<<t|0}enableAll(){this.mask=-1}toggle(t){this.mask^=1<<t|0}disable(t){this.mask&=~(1<<t|0)}disableAll(){this.mask=0}test(t){return(this.mask&t.mask)!==0}isEnabled(t){return(this.mask&(1<<t|0))!==0}},Sy=0,Fg=new B,lo=new wi,ji=new Ce,Kl=new B,Pa=new B,by=new B,wy=new wi,Bg=new B(1,0,0),kg=new B(0,1,0),zg=new B(0,0,1),Vg={type:"added"},Ty={type:"removed"},co={type:"childadded",child:null},Fu={type:"childremoved",child:null},Hn=class s extends ks{constructor(){super(),this.isObject3D=!0,Object.defineProperty(this,"id",{value:Sy++}),this.uuid=Fo(),this.name="",this.type="Object3D",this.parent=null,this.children=[],this.up=s.DEFAULT_UP.clone();let t=new B,e=new mi,n=new wi,i=new B(1,1,1);function r(){n.setFromEuler(e,!1)}function o(){e.setFromQuaternion(n,void 0,!1)}e._onChange(r),n._onChange(o),Object.defineProperties(this,{position:{configurable:!0,enumerable:!0,value:t},rotation:{configurable:!0,enumerable:!0,value:e},quaternion:{configurable:!0,enumerable:!0,value:n},scale:{configurable:!0,enumerable:!0,value:i},modelViewMatrix:{value:new Ce},normalMatrix:{value:new oe}}),this.matrix=new Ce,this.matrixWorld=new Ce,this.matrixAutoUpdate=s.DEFAULT_MATRIX_AUTO_UPDATE,this.matrixWorldAutoUpdate=s.DEFAULT_MATRIX_WORLD_AUTO_UPDATE,this.matrixWorldNeedsUpdate=!1,this.layers=new Ac,this.visible=!0,this.castShadow=!1,this.receiveShadow=!1,this.frustumCulled=!0,this.renderOrder=0,this.animations=[],this.userData={}}onBeforeShadow(){}onAfterShadow(){}onBeforeRender(){}onAfterRender(){}applyMatrix4(t){this.matrixAutoUpdate&&this.updateMatrix(),this.matrix.premultiply(t),this.matrix.decompose(this.position,this.quaternion,this.scale)}applyQuaternion(t){return this.quaternion.premultiply(t),this}setRotationFromAxisAngle(t,e){this.quaternion.setFromAxisAngle(t,e)}setRotationFromEuler(t){this.quaternion.setFromEuler(t,!0)}setRotationFromMatrix(t){this.quaternion.setFromRotationMatrix(t)}setRotationFromQuaternion(t){this.quaternion.copy(t)}rotateOnAxis(t,e){return lo.setFromAxisAngle(t,e),this.quaternion.multiply(lo),this}rotateOnWorldAxis(t,e){return lo.setFromAxisAngle(t,e),this.quaternion.premultiply(lo),this}rotateX(t){return this.rotateOnAxis(Bg,t)}rotateY(t){return this.rotateOnAxis(kg,t)}rotateZ(t){return this.rotateOnAxis(zg,t)}translateOnAxis(t,e){return Fg.copy(t).applyQuaternion(this.quaternion),this.position.add(Fg.multiplyScalar(e)),this}translateX(t){return this.translateOnAxis(Bg,t)}translateY(t){return this.translateOnAxis(kg,t)}translateZ(t){return this.translateOnAxis(zg,t)}localToWorld(t){return this.updateWorldMatrix(!0,!1),t.applyMatrix4(this.matrixWorld)}worldToLocal(t){return this.updateWorldMatrix(!0,!1),t.applyMatrix4(ji.copy(this.matrixWorld).invert())}lookAt(t,e,n){t.isVector3?Kl.copy(t):Kl.set(t,e,n);let i=this.parent;this.updateWorldMatrix(!0,!1),Pa.setFromMatrixPosition(this.matrixWorld),this.isCamera||this.isLight?ji.lookAt(Pa,Kl,this.up):ji.lookAt(Kl,Pa,this.up),this.quaternion.setFromRotationMatrix(ji),i&&(ji.extractRotation(i.matrixWorld),lo.setFromRotationMatrix(ji),this.quaternion.premultiply(lo.invert()))}add(t){if(arguments.length>1){for(let e=0;e<arguments.length;e++)this.add(arguments[e]);return this}return t===this?(console.error("THREE.Object3D.add: object can't be added as a child of itself.",t),this):(t&&t.isObject3D?(t.removeFromParent(),t.parent=this,this.children.push(t),t.dispatchEvent(Vg),co.child=t,this.dispatchEvent(co),co.child=null):console.error("THREE.Object3D.add: object not an instance of THREE.Object3D.",t),this)}remove(t){if(arguments.length>1){for(let n=0;n<arguments.length;n++)this.remove(arguments[n]);return this}let e=this.children.indexOf(t);return e!==-1&&(t.parent=null,this.children.splice(e,1),t.dispatchEvent(Ty),Fu.child=t,this.dispatchEvent(Fu),Fu.child=null),this}removeFromParent(){let t=this.parent;return t!==null&&t.remove(this),this}clear(){return this.remove(...this.children)}attach(t){return this.updateWorldMatrix(!0,!1),ji.copy(this.matrixWorld).invert(),t.parent!==null&&(t.parent.updateWorldMatrix(!0,!1),ji.multiply(t.parent.matrixWorld)),t.applyMatrix4(ji),t.removeFromParent(),t.parent=this,this.children.push(t),t.updateWorldMatrix(!1,!0),t.dispatchEvent(Vg),co.child=t,this.dispatchEvent(co),co.child=null,this}getObjectById(t){return this.getObjectByProperty("id",t)}getObjectByName(t){return this.getObjectByProperty("name",t)}getObjectByProperty(t,e){if(this[t]===e)return this;for(let n=0,i=this.children.length;n<i;n++){let o=this.children[n].getObjectByProperty(t,e);if(o!==void 0)return o}}getObjectsByProperty(t,e,n=[]){this[t]===e&&n.push(this);let i=this.children;for(let r=0,o=i.length;r<o;r++)i[r].getObjectsByProperty(t,e,n);return n}getWorldPosition(t){return this.updateWorldMatrix(!0,!1),t.setFromMatrixPosition(this.matrixWorld)}getWorldQuaternion(t){return this.updateWorldMatrix(!0,!1),this.matrixWorld.decompose(Pa,t,by),t}getWorldScale(t){return this.updateWorldMatrix(!0,!1),this.matrixWorld.decompose(Pa,wy,t),t}getWorldDirection(t){this.updateWorldMatrix(!0,!1);let e=this.matrixWorld.elements;return t.set(e[8],e[9],e[10]).normalize()}raycast(){}traverse(t){t(this);let e=this.children;for(let n=0,i=e.length;n<i;n++)e[n].traverse(t)}traverseVisible(t){if(this.visible===!1)return;t(this);let e=this.children;for(let n=0,i=e.length;n<i;n++)e[n].traverseVisible(t)}traverseAncestors(t){let e=this.parent;e!==null&&(t(e),e.traverseAncestors(t))}updateMatrix(){this.matrix.compose(this.position,this.quaternion,this.scale),this.matrixWorldNeedsUpdate=!0}updateMatrixWorld(t){this.matrixAutoUpdate&&this.updateMatrix(),(this.matrixWorldNeedsUpdate||t)&&(this.matrixWorldAutoUpdate===!0&&(this.parent===null?this.matrixWorld.copy(this.matrix):this.matrixWorld.multiplyMatrices(this.parent.matrixWorld,this.matrix)),this.matrixWorldNeedsUpdate=!1,t=!0);let e=this.children;for(let n=0,i=e.length;n<i;n++)e[n].updateMatrixWorld(t)}updateWorldMatrix(t,e){let n=this.parent;if(t===!0&&n!==null&&n.updateWorldMatrix(!0,!1),this.matrixAutoUpdate&&this.updateMatrix(),this.matrixWorldAutoUpdate===!0&&(this.parent===null?this.matrixWorld.copy(this.matrix):this.matrixWorld.multiplyMatrices(this.parent.matrixWorld,this.matrix)),e===!0){let i=this.children;for(let r=0,o=i.length;r<o;r++)i[r].updateWorldMatrix(!1,!0)}}toJSON(t){let e=t===void 0||typeof t=="string",n={};e&&(t={geometries:{},materials:{},textures:{},images:{},shapes:{},skeletons:{},animations:{},nodes:{}},n.metadata={version:4.6,type:"Object",generator:"Object3D.toJSON"});let i={};i.uuid=this.uuid,i.type=this.type,this.name!==""&&(i.name=this.name),this.castShadow===!0&&(i.castShadow=!0),this.receiveShadow===!0&&(i.receiveShadow=!0),this.visible===!1&&(i.visible=!1),this.frustumCulled===!1&&(i.frustumCulled=!1),this.renderOrder!==0&&(i.renderOrder=this.renderOrder),Object.keys(this.userData).length>0&&(i.userData=this.userData),i.layers=this.layers.mask,i.matrix=this.matrix.toArray(),i.up=this.up.toArray(),this.matrixAutoUpdate===!1&&(i.matrixAutoUpdate=!1),this.isInstancedMesh&&(i.type="InstancedMesh",i.count=this.count,i.instanceMatrix=this.instanceMatrix.toJSON(),this.instanceColor!==null&&(i.instanceColor=this.instanceColor.toJSON())),this.isBatchedMesh&&(i.type="BatchedMesh",i.perObjectFrustumCulled=this.perObjectFrustumCulled,i.sortObjects=this.sortObjects,i.drawRanges=this._drawRanges,i.reservedRanges=this._reservedRanges,i.visibility=this._visibility,i.active=this._active,i.bounds=this._bounds.map(a=>({boxInitialized:a.boxInitialized,boxMin:a.box.min.toArray(),boxMax:a.box.max.toArray(),sphereInitialized:a.sphereInitialized,sphereRadius:a.sphere.radius,sphereCenter:a.sphere.center.toArray()})),i.maxInstanceCount=this._maxInstanceCount,i.maxVertexCount=this._maxVertexCount,i.maxIndexCount=this._maxIndexCount,i.geometryInitialized=this._geometryInitialized,i.geometryCount=this._geometryCount,i.matricesTexture=this._matricesTexture.toJSON(t),this._colorsTexture!==null&&(i.colorsTexture=this._colorsTexture.toJSON(t)),this.boundingSphere!==null&&(i.boundingSphere={center:i.boundingSphere.center.toArray(),radius:i.boundingSphere.radius}),this.boundingBox!==null&&(i.boundingBox={min:i.boundingBox.min.toArray(),max:i.boundingBox.max.toArray()}));function r(a,l){return a[l.uuid]===void 0&&(a[l.uuid]=l.toJSON(t)),l.uuid}if(this.isScene)this.background&&(this.background.isColor?i.background=this.background.toJSON():this.background.isTexture&&(i.background=this.background.toJSON(t).uuid)),this.environment&&this.environment.isTexture&&this.environment.isRenderTargetTexture!==!0&&(i.environment=this.environment.toJSON(t).uuid);else if(this.isMesh||this.isLine||this.isPoints){i.geometry=r(t.geometries,this.geometry);let a=this.geometry.parameters;if(a!==void 0&&a.shapes!==void 0){let l=a.shapes;if(Array.isArray(l))for(let c=0,h=l.length;c<h;c++){let u=l[c];r(t.shapes,u)}else r(t.shapes,l)}}if(this.isSkinnedMesh&&(i.bindMode=this.bindMode,i.bindMatrix=this.bindMatrix.toArray(),this.skeleton!==void 0&&(r(t.skeletons,this.skeleton),i.skeleton=this.skeleton.uuid)),this.material!==void 0)if(Array.isArray(this.material)){let a=[];for(let l=0,c=this.material.length;l<c;l++)a.push(r(t.materials,this.material[l]));i.material=a}else i.material=r(t.materials,this.material);if(this.children.length>0){i.children=[];for(let a=0;a<this.children.length;a++)i.children.push(this.children[a].toJSON(t).object)}if(this.animations.length>0){i.animations=[];for(let a=0;a<this.animations.length;a++){let l=this.animations[a];i.animations.push(r(t.animations,l))}}if(e){let a=o(t.geometries),l=o(t.materials),c=o(t.textures),h=o(t.images),u=o(t.shapes),f=o(t.skeletons),d=o(t.animations),g=o(t.nodes);a.length>0&&(n.geometries=a),l.length>0&&(n.materials=l),c.length>0&&(n.textures=c),h.length>0&&(n.images=h),u.length>0&&(n.shapes=u),f.length>0&&(n.skeletons=f),d.length>0&&(n.animations=d),g.length>0&&(n.nodes=g)}return n.object=i,n;function o(a){let l=[];for(let c in a){let h=a[c];delete h.metadata,l.push(h)}return l}}clone(t){return new this.constructor().copy(this,t)}copy(t,e=!0){if(this.name=t.name,this.up.copy(t.up),this.position.copy(t.position),this.rotation.order=t.rotation.order,this.quaternion.copy(t.quaternion),this.scale.copy(t.scale),this.matrix.copy(t.matrix),this.matrixWorld.copy(t.matrixWorld),this.matrixAutoUpdate=t.matrixAutoUpdate,this.matrixWorldAutoUpdate=t.matrixWorldAutoUpdate,this.matrixWorldNeedsUpdate=t.matrixWorldNeedsUpdate,this.layers.mask=t.layers.mask,this.visible=t.visible,this.castShadow=t.castShadow,this.receiveShadow=t.receiveShadow,this.frustumCulled=t.frustumCulled,this.renderOrder=t.renderOrder,this.animations=t.animations.slice(),this.userData=JSON.parse(JSON.stringify(t.userData)),e===!0)for(let n=0;n<t.children.length;n++){let i=t.children[n];this.add(i.clone())}return this}};Hn.DEFAULT_UP=new B(0,1,0);Hn.DEFAULT_MATRIX_AUTO_UPDATE=!0;Hn.DEFAULT_MATRIX_WORLD_AUTO_UPDATE=!0;var Si=new B,ts=new B,Bu=new B,es=new B,ho=new B,uo=new B,Hg=new B,ku=new B,zu=new B,Vu=new B,Hu=new Ae,Gu=new Ae,Wu=new Ae,_r=class s{constructor(t=new B,e=new B,n=new B){this.a=t,this.b=e,this.c=n}static getNormal(t,e,n,i){i.subVectors(n,e),Si.subVectors(t,e),i.cross(Si);let r=i.lengthSq();return r>0?i.multiplyScalar(1/Math.sqrt(r)):i.set(0,0,0)}static getBarycoord(t,e,n,i,r){Si.subVectors(i,e),ts.subVectors(n,e),Bu.subVectors(t,e);let o=Si.dot(Si),a=Si.dot(ts),l=Si.dot(Bu),c=ts.dot(ts),h=ts.dot(Bu),u=o*c-a*a;if(u===0)return r.set(0,0,0),null;let f=1/u,d=(c*l-a*h)*f,g=(o*h-a*l)*f;return r.set(1-d-g,g,d)}static containsPoint(t,e,n,i){return this.getBarycoord(t,e,n,i,es)===null?!1:es.x>=0&&es.y>=0&&es.x+es.y<=1}static getInterpolation(t,e,n,i,r,o,a,l){return this.getBarycoord(t,e,n,i,es)===null?(l.x=0,l.y=0,"z"in l&&(l.z=0),"w"in l&&(l.w=0),null):(l.setScalar(0),l.addScaledVector(r,es.x),l.addScaledVector(o,es.y),l.addScaledVector(a,es.z),l)}static getInterpolatedAttribute(t,e,n,i,r,o){return Hu.setScalar(0),Gu.setScalar(0),Wu.setScalar(0),Hu.fromBufferAttribute(t,e),Gu.fromBufferAttribute(t,n),Wu.fromBufferAttribute(t,i),o.setScalar(0),o.addScaledVector(Hu,r.x),o.addScaledVector(Gu,r.y),o.addScaledVector(Wu,r.z),o}static isFrontFacing(t,e,n,i){return Si.subVectors(n,e),ts.subVectors(t,e),Si.cross(ts).dot(i)<0}set(t,e,n){return this.a.copy(t),this.b.copy(e),this.c.copy(n),this}setFromPointsAndIndices(t,e,n,i){return this.a.copy(t[e]),this.b.copy(t[n]),this.c.copy(t[i]),this}setFromAttributeAndIndices(t,e,n,i){return this.a.fromBufferAttribute(t,e),this.b.fromBufferAttribute(t,n),this.c.fromBufferAttribute(t,i),this}clone(){return new this.constructor().copy(this)}copy(t){return this.a.copy(t.a),this.b.copy(t.b),this.c.copy(t.c),this}getArea(){return Si.subVectors(this.c,this.b),ts.subVectors(this.a,this.b),Si.cross(ts).length()*.5}getMidpoint(t){return t.addVectors(this.a,this.b).add(this.c).multiplyScalar(1/3)}getNormal(t){return s.getNormal(this.a,this.b,this.c,t)}getPlane(t){return t.setFromCoplanarPoints(this.a,this.b,this.c)}getBarycoord(t,e){return s.getBarycoord(t,this.a,this.b,this.c,e)}getInterpolation(t,e,n,i,r){return s.getInterpolation(t,this.a,this.b,this.c,e,n,i,r)}containsPoint(t){return s.containsPoint(t,this.a,this.b,this.c)}isFrontFacing(t){return s.isFrontFacing(this.a,this.b,this.c,t)}intersectsBox(t){return t.intersectsTriangle(this)}closestPointToPoint(t,e){let n=this.a,i=this.b,r=this.c,o,a;ho.subVectors(i,n),uo.subVectors(r,n),ku.subVectors(t,n);let l=ho.dot(ku),c=uo.dot(ku);if(l<=0&&c<=0)return e.copy(n);zu.subVectors(t,i);let h=ho.dot(zu),u=uo.dot(zu);if(h>=0&&u<=h)return e.copy(i);let f=l*u-h*c;if(f<=0&&l>=0&&h<=0)return o=l/(l-h),e.copy(n).addScaledVector(ho,o);Vu.subVectors(t,r);let d=ho.dot(Vu),g=uo.dot(Vu);if(g>=0&&d<=g)return e.copy(r);let _=d*c-l*g;if(_<=0&&c>=0&&g<=0)return a=c/(c-g),e.copy(n).addScaledVector(uo,a);let m=h*g-d*u;if(m<=0&&u-h>=0&&d-g>=0)return Hg.subVectors(r,i),a=(u-h)/(u-h+(d-g)),e.copy(i).addScaledVector(Hg,a);let p=1/(m+_+f);return o=_*p,a=f*p,e.copy(n).addScaledVector(ho,o).addScaledVector(uo,a)}equals(t){return t.a.equals(this.a)&&t.b.equals(this.b)&&t.c.equals(this.c)}},G_={aliceblue:15792383,antiquewhite:16444375,aqua:65535,aquamarine:8388564,azure:15794175,beige:16119260,bisque:16770244,black:0,blanchedalmond:16772045,blue:255,blueviolet:9055202,brown:10824234,burlywood:14596231,cadetblue:6266528,chartreuse:8388352,chocolate:13789470,coral:16744272,cornflowerblue:6591981,cornsilk:16775388,crimson:14423100,cyan:65535,darkblue:139,darkcyan:35723,darkgoldenrod:12092939,darkgray:11119017,darkgreen:25600,darkgrey:11119017,darkkhaki:12433259,darkmagenta:9109643,darkolivegreen:5597999,darkorange:16747520,darkorchid:10040012,darkred:9109504,darksalmon:15308410,darkseagreen:9419919,darkslateblue:4734347,darkslategray:3100495,darkslategrey:3100495,darkturquoise:52945,darkviolet:9699539,deeppink:16716947,deepskyblue:49151,dimgray:6908265,dimgrey:6908265,dodgerblue:2003199,firebrick:11674146,floralwhite:16775920,forestgreen:2263842,fuchsia:16711935,gainsboro:14474460,ghostwhite:16316671,gold:16766720,goldenrod:14329120,gray:8421504,green:32768,greenyellow:11403055,grey:8421504,honeydew:15794160,hotpink:16738740,indianred:13458524,indigo:4915330,ivory:16777200,khaki:15787660,lavender:15132410,lavenderblush:16773365,lawngreen:8190976,lemonchiffon:16775885,lightblue:11393254,lightcoral:15761536,lightcyan:14745599,lightgoldenrodyellow:16448210,lightgray:13882323,lightgreen:9498256,lightgrey:13882323,lightpink:16758465,lightsalmon:16752762,lightseagreen:2142890,lightskyblue:8900346,lightslategray:7833753,lightslategrey:7833753,lightsteelblue:11584734,lightyellow:16777184,lime:65280,limegreen:3329330,linen:16445670,magenta:16711935,maroon:8388608,mediumaquamarine:6737322,mediumblue:205,mediumorchid:12211667,mediumpurple:9662683,mediumseagreen:3978097,mediumslateblue:8087790,mediumspringgreen:64154,mediumturquoise:4772300,mediumvioletred:13047173,midnightblue:1644912,mintcream:16121850,mistyrose:16770273,moccasin:16770229,navajowhite:16768685,navy:128,oldlace:16643558,olive:8421376,olivedrab:7048739,orange:16753920,orangered:16729344,orchid:14315734,palegoldenrod:15657130,palegreen:10025880,paleturquoise:11529966,palevioletred:14381203,papayawhip:16773077,peachpuff:16767673,peru:13468991,pink:16761035,plum:14524637,powderblue:11591910,purple:8388736,rebeccapurple:6697881,red:16711680,rosybrown:12357519,royalblue:4286945,saddlebrown:9127187,salmon:16416882,sandybrown:16032864,seagreen:3050327,seashell:16774638,sienna:10506797,silver:12632256,skyblue:8900331,slateblue:6970061,slategray:7372944,slategrey:7372944,snow:16775930,springgreen:65407,steelblue:4620980,tan:13808780,teal:32896,thistle:14204888,tomato:16737095,turquoise:4251856,violet:15631086,wheat:16113331,white:16777215,whitesmoke:16119285,yellow:16776960,yellowgreen:10145074},Ls={h:0,s:0,l:0},Ql={h:0,s:0,l:0};function Xu(s,t,e){return e<0&&(e+=1),e>1&&(e-=1),e<1/6?s+(t-s)*6*e:e<1/2?t:e<2/3?s+(t-s)*6*(2/3-e):s}var se=class{constructor(t,e,n){return this.isColor=!0,this.r=1,this.g=1,this.b=1,this.set(t,e,n)}set(t,e,n){if(e===void 0&&n===void 0){let i=t;i&&i.isColor?this.copy(i):typeof i=="number"?this.setHex(i):typeof i=="string"&&this.setStyle(i)}else this.setRGB(t,e,n);return this}setScalar(t){return this.r=t,this.g=t,this.b=t,this}setHex(t,e=Mn){return t=Math.floor(t),this.r=(t>>16&255)/255,this.g=(t>>8&255)/255,this.b=(t&255)/255,ge.toWorkingColorSpace(this,e),this}setRGB(t,e,n,i=ge.workingColorSpace){return this.r=t,this.g=e,this.b=n,ge.toWorkingColorSpace(this,i),this}setHSL(t,e,n,i=ge.workingColorSpace){if(t=fy(t,1),e=Sn(e,0,1),n=Sn(n,0,1),e===0)this.r=this.g=this.b=n;else{let r=n<=.5?n*(1+e):n+e-n*e,o=2*n-r;this.r=Xu(o,r,t+1/3),this.g=Xu(o,r,t),this.b=Xu(o,r,t-1/3)}return ge.toWorkingColorSpace(this,i),this}setStyle(t,e=Mn){function n(r){r!==void 0&&parseFloat(r)<1&&console.warn("THREE.Color: Alpha component of "+t+" will be ignored.")}let i;if(i=/^(\w+)\(([^\)]*)\)/.exec(t)){let r,o=i[1],a=i[2];switch(o){case"rgb":case"rgba":if(r=/^\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(a))return n(r[4]),this.setRGB(Math.min(255,parseInt(r[1],10))/255,Math.min(255,parseInt(r[2],10))/255,Math.min(255,parseInt(r[3],10))/255,e);if(r=/^\s*(\d+)\%\s*,\s*(\d+)\%\s*,\s*(\d+)\%\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(a))return n(r[4]),this.setRGB(Math.min(100,parseInt(r[1],10))/100,Math.min(100,parseInt(r[2],10))/100,Math.min(100,parseInt(r[3],10))/100,e);break;case"hsl":case"hsla":if(r=/^\s*(\d*\.?\d+)\s*,\s*(\d*\.?\d+)\%\s*,\s*(\d*\.?\d+)\%\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(a))return n(r[4]),this.setHSL(parseFloat(r[1])/360,parseFloat(r[2])/100,parseFloat(r[3])/100,e);break;default:console.warn("THREE.Color: Unknown color model "+t)}}else if(i=/^\#([A-Fa-f\d]+)$/.exec(t)){let r=i[1],o=r.length;if(o===3)return this.setRGB(parseInt(r.charAt(0),16)/15,parseInt(r.charAt(1),16)/15,parseInt(r.charAt(2),16)/15,e);if(o===6)return this.setHex(parseInt(r,16),e);console.warn("THREE.Color: Invalid hex color "+t)}else if(t&&t.length>0)return this.setColorName(t,e);return this}setColorName(t,e=Mn){let n=G_[t.toLowerCase()];return n!==void 0?this.setHex(n,e):console.warn("THREE.Color: Unknown color "+t),this}clone(){return new this.constructor(this.r,this.g,this.b)}copy(t){return this.r=t.r,this.g=t.g,this.b=t.b,this}copySRGBToLinear(t){return this.r=rs(t.r),this.g=rs(t.g),this.b=rs(t.b),this}copyLinearToSRGB(t){return this.r=So(t.r),this.g=So(t.g),this.b=So(t.b),this}convertSRGBToLinear(){return this.copySRGBToLinear(this),this}convertLinearToSRGB(){return this.copyLinearToSRGB(this),this}getHex(t=Mn){return ge.fromWorkingColorSpace(yn.copy(this),t),Math.round(Sn(yn.r*255,0,255))*65536+Math.round(Sn(yn.g*255,0,255))*256+Math.round(Sn(yn.b*255,0,255))}getHexString(t=Mn){return("000000"+this.getHex(t).toString(16)).slice(-6)}getHSL(t,e=ge.workingColorSpace){ge.fromWorkingColorSpace(yn.copy(this),e);let n=yn.r,i=yn.g,r=yn.b,o=Math.max(n,i,r),a=Math.min(n,i,r),l,c,h=(a+o)/2;if(a===o)l=0,c=0;else{let u=o-a;switch(c=h<=.5?u/(o+a):u/(2-o-a),o){case n:l=(i-r)/u+(i<r?6:0);break;case i:l=(r-n)/u+2;break;case r:l=(n-i)/u+4;break}l/=6}return t.h=l,t.s=c,t.l=h,t}getRGB(t,e=ge.workingColorSpace){return ge.fromWorkingColorSpace(yn.copy(this),e),t.r=yn.r,t.g=yn.g,t.b=yn.b,t}getStyle(t=Mn){ge.fromWorkingColorSpace(yn.copy(this),t);let e=yn.r,n=yn.g,i=yn.b;return t!==Mn?`color(${t} ${e.toFixed(3)} ${n.toFixed(3)} ${i.toFixed(3)})`:`rgb(${Math.round(e*255)},${Math.round(n*255)},${Math.round(i*255)})`}offsetHSL(t,e,n){return this.getHSL(Ls),this.setHSL(Ls.h+t,Ls.s+e,Ls.l+n)}add(t){return this.r+=t.r,this.g+=t.g,this.b+=t.b,this}addColors(t,e){return this.r=t.r+e.r,this.g=t.g+e.g,this.b=t.b+e.b,this}addScalar(t){return this.r+=t,this.g+=t,this.b+=t,this}sub(t){return this.r=Math.max(0,this.r-t.r),this.g=Math.max(0,this.g-t.g),this.b=Math.max(0,this.b-t.b),this}multiply(t){return this.r*=t.r,this.g*=t.g,this.b*=t.b,this}multiplyScalar(t){return this.r*=t,this.g*=t,this.b*=t,this}lerp(t,e){return this.r+=(t.r-this.r)*e,this.g+=(t.g-this.g)*e,this.b+=(t.b-this.b)*e,this}lerpColors(t,e,n){return this.r=t.r+(e.r-t.r)*n,this.g=t.g+(e.g-t.g)*n,this.b=t.b+(e.b-t.b)*n,this}lerpHSL(t,e){this.getHSL(Ls),t.getHSL(Ql);let n=Cu(Ls.h,Ql.h,e),i=Cu(Ls.s,Ql.s,e),r=Cu(Ls.l,Ql.l,e);return this.setHSL(n,i,r),this}setFromVector3(t){return this.r=t.x,this.g=t.y,this.b=t.z,this}applyMatrix3(t){let e=this.r,n=this.g,i=this.b,r=t.elements;return this.r=r[0]*e+r[3]*n+r[6]*i,this.g=r[1]*e+r[4]*n+r[7]*i,this.b=r[2]*e+r[5]*n+r[8]*i,this}equals(t){return t.r===this.r&&t.g===this.g&&t.b===this.b}fromArray(t,e=0){return this.r=t[e],this.g=t[e+1],this.b=t[e+2],this}toArray(t=[],e=0){return t[e]=this.r,t[e+1]=this.g,t[e+2]=this.b,t}fromBufferAttribute(t,e){return this.r=t.getX(e),this.g=t.getY(e),this.b=t.getZ(e),this}toJSON(){return this.getHex()}*[Symbol.iterator](){yield this.r,yield this.g,yield this.b}},yn=new se;se.NAMES=G_;var Ey=0,br=class extends ks{static get type(){return"Material"}get type(){return this.constructor.type}set type(t){}constructor(){super(),this.isMaterial=!0,Object.defineProperty(this,"id",{value:Ey++}),this.uuid=Fo(),this.name="",this.blending=yo,this.side=Bs,this.vertexColors=!1,this.opacity=1,this.transparent=!1,this.alphaHash=!1,this.blendSrc=af,this.blendDst=lf,this.blendEquation=gr,this.blendSrcAlpha=null,this.blendDstAlpha=null,this.blendEquationAlpha=null,this.blendColor=new se(0,0,0),this.blendAlpha=0,this.depthFunc=wo,this.depthTest=!0,this.depthWrite=!0,this.stencilWriteMask=255,this.stencilFunc=Tg,this.stencilRef=0,this.stencilFuncMask=255,this.stencilFail=no,this.stencilZFail=no,this.stencilZPass=no,this.stencilWrite=!1,this.clippingPlanes=null,this.clipIntersection=!1,this.clipShadows=!1,this.shadowSide=null,this.colorWrite=!0,this.precision=null,this.polygonOffset=!1,this.polygonOffsetFactor=0,this.polygonOffsetUnits=0,this.dithering=!1,this.alphaToCoverage=!1,this.premultipliedAlpha=!1,this.forceSinglePass=!1,this.visible=!0,this.toneMapped=!0,this.userData={},this.version=0,this._alphaTest=0}get alphaTest(){return this._alphaTest}set alphaTest(t){this._alphaTest>0!=t>0&&this.version++,this._alphaTest=t}onBeforeRender(){}onBeforeCompile(){}customProgramCacheKey(){return this.onBeforeCompile.toString()}setValues(t){if(t!==void 0)for(let e in t){let n=t[e];if(n===void 0){console.warn(`THREE.Material: parameter '${e}' has value of undefined.`);continue}let i=this[e];if(i===void 0){console.warn(`THREE.Material: '${e}' is not a property of THREE.${this.type}.`);continue}i&&i.isColor?i.set(n):i&&i.isVector3&&n&&n.isVector3?i.copy(n):this[e]=n}}toJSON(t){let e=t===void 0||typeof t=="string";e&&(t={textures:{},images:{}});let n={metadata:{version:4.6,type:"Material",generator:"Material.toJSON"}};n.uuid=this.uuid,n.type=this.type,this.name!==""&&(n.name=this.name),this.color&&this.color.isColor&&(n.color=this.color.getHex()),this.roughness!==void 0&&(n.roughness=this.roughness),this.metalness!==void 0&&(n.metalness=this.metalness),this.sheen!==void 0&&(n.sheen=this.sheen),this.sheenColor&&this.sheenColor.isColor&&(n.sheenColor=this.sheenColor.getHex()),this.sheenRoughness!==void 0&&(n.sheenRoughness=this.sheenRoughness),this.emissive&&this.emissive.isColor&&(n.emissive=this.emissive.getHex()),this.emissiveIntensity!==void 0&&this.emissiveIntensity!==1&&(n.emissiveIntensity=this.emissiveIntensity),this.specular&&this.specular.isColor&&(n.specular=this.specular.getHex()),this.specularIntensity!==void 0&&(n.specularIntensity=this.specularIntensity),this.specularColor&&this.specularColor.isColor&&(n.specularColor=this.specularColor.getHex()),this.shininess!==void 0&&(n.shininess=this.shininess),this.clearcoat!==void 0&&(n.clearcoat=this.clearcoat),this.clearcoatRoughness!==void 0&&(n.clearcoatRoughness=this.clearcoatRoughness),this.clearcoatMap&&this.clearcoatMap.isTexture&&(n.clearcoatMap=this.clearcoatMap.toJSON(t).uuid),this.clearcoatRoughnessMap&&this.clearcoatRoughnessMap.isTexture&&(n.clearcoatRoughnessMap=this.clearcoatRoughnessMap.toJSON(t).uuid),this.clearcoatNormalMap&&this.clearcoatNormalMap.isTexture&&(n.clearcoatNormalMap=this.clearcoatNormalMap.toJSON(t).uuid,n.clearcoatNormalScale=this.clearcoatNormalScale.toArray()),this.dispersion!==void 0&&(n.dispersion=this.dispersion),this.iridescence!==void 0&&(n.iridescence=this.iridescence),this.iridescenceIOR!==void 0&&(n.iridescenceIOR=this.iridescenceIOR),this.iridescenceThicknessRange!==void 0&&(n.iridescenceThicknessRange=this.iridescenceThicknessRange),this.iridescenceMap&&this.iridescenceMap.isTexture&&(n.iridescenceMap=this.iridescenceMap.toJSON(t).uuid),this.iridescenceThicknessMap&&this.iridescenceThicknessMap.isTexture&&(n.iridescenceThicknessMap=this.iridescenceThicknessMap.toJSON(t).uuid),this.anisotropy!==void 0&&(n.anisotropy=this.anisotropy),this.anisotropyRotation!==void 0&&(n.anisotropyRotation=this.anisotropyRotation),this.anisotropyMap&&this.anisotropyMap.isTexture&&(n.anisotropyMap=this.anisotropyMap.toJSON(t).uuid),this.map&&this.map.isTexture&&(n.map=this.map.toJSON(t).uuid),this.matcap&&this.matcap.isTexture&&(n.matcap=this.matcap.toJSON(t).uuid),this.alphaMap&&this.alphaMap.isTexture&&(n.alphaMap=this.alphaMap.toJSON(t).uuid),this.lightMap&&this.lightMap.isTexture&&(n.lightMap=this.lightMap.toJSON(t).uuid,n.lightMapIntensity=this.lightMapIntensity),this.aoMap&&this.aoMap.isTexture&&(n.aoMap=this.aoMap.toJSON(t).uuid,n.aoMapIntensity=this.aoMapIntensity),this.bumpMap&&this.bumpMap.isTexture&&(n.bumpMap=this.bumpMap.toJSON(t).uuid,n.bumpScale=this.bumpScale),this.normalMap&&this.normalMap.isTexture&&(n.normalMap=this.normalMap.toJSON(t).uuid,n.normalMapType=this.normalMapType,n.normalScale=this.normalScale.toArray()),this.displacementMap&&this.displacementMap.isTexture&&(n.displacementMap=this.displacementMap.toJSON(t).uuid,n.displacementScale=this.displacementScale,n.displacementBias=this.displacementBias),this.roughnessMap&&this.roughnessMap.isTexture&&(n.roughnessMap=this.roughnessMap.toJSON(t).uuid),this.metalnessMap&&this.metalnessMap.isTexture&&(n.metalnessMap=this.metalnessMap.toJSON(t).uuid),this.emissiveMap&&this.emissiveMap.isTexture&&(n.emissiveMap=this.emissiveMap.toJSON(t).uuid),this.specularMap&&this.specularMap.isTexture&&(n.specularMap=this.specularMap.toJSON(t).uuid),this.specularIntensityMap&&this.specularIntensityMap.isTexture&&(n.specularIntensityMap=this.specularIntensityMap.toJSON(t).uuid),this.specularColorMap&&this.specularColorMap.isTexture&&(n.specularColorMap=this.specularColorMap.toJSON(t).uuid),this.envMap&&this.envMap.isTexture&&(n.envMap=this.envMap.toJSON(t).uuid,this.combine!==void 0&&(n.combine=this.combine)),this.envMapRotation!==void 0&&(n.envMapRotation=this.envMapRotation.toArray()),this.envMapIntensity!==void 0&&(n.envMapIntensity=this.envMapIntensity),this.reflectivity!==void 0&&(n.reflectivity=this.reflectivity),this.refractionRatio!==void 0&&(n.refractionRatio=this.refractionRatio),this.gradientMap&&this.gradientMap.isTexture&&(n.gradientMap=this.gradientMap.toJSON(t).uuid),this.transmission!==void 0&&(n.transmission=this.transmission),this.transmissionMap&&this.transmissionMap.isTexture&&(n.transmissionMap=this.transmissionMap.toJSON(t).uuid),this.thickness!==void 0&&(n.thickness=this.thickness),this.thicknessMap&&this.thicknessMap.isTexture&&(n.thicknessMap=this.thicknessMap.toJSON(t).uuid),this.attenuationDistance!==void 0&&this.attenuationDistance!==1/0&&(n.attenuationDistance=this.attenuationDistance),this.attenuationColor!==void 0&&(n.attenuationColor=this.attenuationColor.getHex()),this.size!==void 0&&(n.size=this.size),this.shadowSide!==null&&(n.shadowSide=this.shadowSide),this.sizeAttenuation!==void 0&&(n.sizeAttenuation=this.sizeAttenuation),this.blending!==yo&&(n.blending=this.blending),this.side!==Bs&&(n.side=this.side),this.vertexColors===!0&&(n.vertexColors=!0),this.opacity<1&&(n.opacity=this.opacity),this.transparent===!0&&(n.transparent=!0),this.blendSrc!==af&&(n.blendSrc=this.blendSrc),this.blendDst!==lf&&(n.blendDst=this.blendDst),this.blendEquation!==gr&&(n.blendEquation=this.blendEquation),this.blendSrcAlpha!==null&&(n.blendSrcAlpha=this.blendSrcAlpha),this.blendDstAlpha!==null&&(n.blendDstAlpha=this.blendDstAlpha),this.blendEquationAlpha!==null&&(n.blendEquationAlpha=this.blendEquationAlpha),this.blendColor&&this.blendColor.isColor&&(n.blendColor=this.blendColor.getHex()),this.blendAlpha!==0&&(n.blendAlpha=this.blendAlpha),this.depthFunc!==wo&&(n.depthFunc=this.depthFunc),this.depthTest===!1&&(n.depthTest=this.depthTest),this.depthWrite===!1&&(n.depthWrite=this.depthWrite),this.colorWrite===!1&&(n.colorWrite=this.colorWrite),this.stencilWriteMask!==255&&(n.stencilWriteMask=this.stencilWriteMask),this.stencilFunc!==Tg&&(n.stencilFunc=this.stencilFunc),this.stencilRef!==0&&(n.stencilRef=this.stencilRef),this.stencilFuncMask!==255&&(n.stencilFuncMask=this.stencilFuncMask),this.stencilFail!==no&&(n.stencilFail=this.stencilFail),this.stencilZFail!==no&&(n.stencilZFail=this.stencilZFail),this.stencilZPass!==no&&(n.stencilZPass=this.stencilZPass),this.stencilWrite===!0&&(n.stencilWrite=this.stencilWrite),this.rotation!==void 0&&this.rotation!==0&&(n.rotation=this.rotation),this.polygonOffset===!0&&(n.polygonOffset=!0),this.polygonOffsetFactor!==0&&(n.polygonOffsetFactor=this.polygonOffsetFactor),this.polygonOffsetUnits!==0&&(n.polygonOffsetUnits=this.polygonOffsetUnits),this.linewidth!==void 0&&this.linewidth!==1&&(n.linewidth=this.linewidth),this.dashSize!==void 0&&(n.dashSize=this.dashSize),this.gapSize!==void 0&&(n.gapSize=this.gapSize),this.scale!==void 0&&(n.scale=this.scale),this.dithering===!0&&(n.dithering=!0),this.alphaTest>0&&(n.alphaTest=this.alphaTest),this.alphaHash===!0&&(n.alphaHash=!0),this.alphaToCoverage===!0&&(n.alphaToCoverage=!0),this.premultipliedAlpha===!0&&(n.premultipliedAlpha=!0),this.forceSinglePass===!0&&(n.forceSinglePass=!0),this.wireframe===!0&&(n.wireframe=!0),this.wireframeLinewidth>1&&(n.wireframeLinewidth=this.wireframeLinewidth),this.wireframeLinecap!=="round"&&(n.wireframeLinecap=this.wireframeLinecap),this.wireframeLinejoin!=="round"&&(n.wireframeLinejoin=this.wireframeLinejoin),this.flatShading===!0&&(n.flatShading=!0),this.visible===!1&&(n.visible=!1),this.toneMapped===!1&&(n.toneMapped=!1),this.fog===!1&&(n.fog=!1),Object.keys(this.userData).length>0&&(n.userData=this.userData);function i(r){let o=[];for(let a in r){let l=r[a];delete l.metadata,o.push(l)}return o}if(e){let r=i(t.textures),o=i(t.images);r.length>0&&(n.textures=r),o.length>0&&(n.images=o)}return n}clone(){return new this.constructor().copy(this)}copy(t){this.name=t.name,this.blending=t.blending,this.side=t.side,this.vertexColors=t.vertexColors,this.opacity=t.opacity,this.transparent=t.transparent,this.blendSrc=t.blendSrc,this.blendDst=t.blendDst,this.blendEquation=t.blendEquation,this.blendSrcAlpha=t.blendSrcAlpha,this.blendDstAlpha=t.blendDstAlpha,this.blendEquationAlpha=t.blendEquationAlpha,this.blendColor.copy(t.blendColor),this.blendAlpha=t.blendAlpha,this.depthFunc=t.depthFunc,this.depthTest=t.depthTest,this.depthWrite=t.depthWrite,this.stencilWriteMask=t.stencilWriteMask,this.stencilFunc=t.stencilFunc,this.stencilRef=t.stencilRef,this.stencilFuncMask=t.stencilFuncMask,this.stencilFail=t.stencilFail,this.stencilZFail=t.stencilZFail,this.stencilZPass=t.stencilZPass,this.stencilWrite=t.stencilWrite;let e=t.clippingPlanes,n=null;if(e!==null){let i=e.length;n=new Array(i);for(let r=0;r!==i;++r)n[r]=e[r].clone()}return this.clippingPlanes=n,this.clipIntersection=t.clipIntersection,this.clipShadows=t.clipShadows,this.shadowSide=t.shadowSide,this.colorWrite=t.colorWrite,this.precision=t.precision,this.polygonOffset=t.polygonOffset,this.polygonOffsetFactor=t.polygonOffsetFactor,this.polygonOffsetUnits=t.polygonOffsetUnits,this.dithering=t.dithering,this.alphaTest=t.alphaTest,this.alphaHash=t.alphaHash,this.alphaToCoverage=t.alphaToCoverage,this.premultipliedAlpha=t.premultipliedAlpha,this.forceSinglePass=t.forceSinglePass,this.visible=t.visible,this.toneMapped=t.toneMapped,this.userData=JSON.parse(JSON.stringify(t.userData)),this}dispose(){this.dispatchEvent({type:"dispose"})}set needsUpdate(t){t===!0&&this.version++}onBuild(){console.warn("Material: onBuild() has been removed.")}},Ti=class extends br{static get type(){return"MeshBasicMaterial"}constructor(t){super(),this.isMeshBasicMaterial=!0,this.color=new se(16777215),this.map=null,this.lightMap=null,this.lightMapIntensity=1,this.aoMap=null,this.aoMapIntensity=1,this.specularMap=null,this.alphaMap=null,this.envMap=null,this.envMapRotation=new mi,this.combine=R_,this.reflectivity=1,this.refractionRatio=.98,this.wireframe=!1,this.wireframeLinewidth=1,this.wireframeLinecap="round",this.wireframeLinejoin="round",this.fog=!0,this.setValues(t)}copy(t){return super.copy(t),this.color.copy(t.color),this.map=t.map,this.lightMap=t.lightMap,this.lightMapIntensity=t.lightMapIntensity,this.aoMap=t.aoMap,this.aoMapIntensity=t.aoMapIntensity,this.specularMap=t.specularMap,this.alphaMap=t.alphaMap,this.envMap=t.envMap,this.envMapRotation.copy(t.envMapRotation),this.combine=t.combine,this.reflectivity=t.reflectivity,this.refractionRatio=t.refractionRatio,this.wireframe=t.wireframe,this.wireframeLinewidth=t.wireframeLinewidth,this.wireframeLinecap=t.wireframeLinecap,this.wireframeLinejoin=t.wireframeLinejoin,this.fog=t.fog,this}};var Je=new B,jl=new vt,ti=class{constructor(t,e,n=!1){if(Array.isArray(t))throw new TypeError("THREE.BufferAttribute: array should be a Typed Array.");this.isBufferAttribute=!0,this.name="",this.array=t,this.itemSize=e,this.count=t!==void 0?t.length/e:0,this.normalized=n,this.usage=Eg,this.updateRanges=[],this.gpuType=Bi,this.version=0}onUploadCallback(){}set needsUpdate(t){t===!0&&this.version++}setUsage(t){return this.usage=t,this}addUpdateRange(t,e){this.updateRanges.push({start:t,count:e})}clearUpdateRanges(){this.updateRanges.length=0}copy(t){return this.name=t.name,this.array=new t.array.constructor(t.array),this.itemSize=t.itemSize,this.count=t.count,this.normalized=t.normalized,this.usage=t.usage,this.gpuType=t.gpuType,this}copyAt(t,e,n){t*=this.itemSize,n*=e.itemSize;for(let i=0,r=this.itemSize;i<r;i++)this.array[t+i]=e.array[n+i];return this}copyArray(t){return this.array.set(t),this}applyMatrix3(t){if(this.itemSize===2)for(let e=0,n=this.count;e<n;e++)jl.fromBufferAttribute(this,e),jl.applyMatrix3(t),this.setXY(e,jl.x,jl.y);else if(this.itemSize===3)for(let e=0,n=this.count;e<n;e++)Je.fromBufferAttribute(this,e),Je.applyMatrix3(t),this.setXYZ(e,Je.x,Je.y,Je.z);return this}applyMatrix4(t){for(let e=0,n=this.count;e<n;e++)Je.fromBufferAttribute(this,e),Je.applyMatrix4(t),this.setXYZ(e,Je.x,Je.y,Je.z);return this}applyNormalMatrix(t){for(let e=0,n=this.count;e<n;e++)Je.fromBufferAttribute(this,e),Je.applyNormalMatrix(t),this.setXYZ(e,Je.x,Je.y,Je.z);return this}transformDirection(t){for(let e=0,n=this.count;e<n;e++)Je.fromBufferAttribute(this,e),Je.transformDirection(t),this.setXYZ(e,Je.x,Je.y,Je.z);return this}set(t,e=0){return this.array.set(t,e),this}getComponent(t,e){let n=this.array[t*this.itemSize+e];return this.normalized&&(n=Aa(n,this.array)),n}setComponent(t,e,n){return this.normalized&&(n=zn(n,this.array)),this.array[t*this.itemSize+e]=n,this}getX(t){let e=this.array[t*this.itemSize];return this.normalized&&(e=Aa(e,this.array)),e}setX(t,e){return this.normalized&&(e=zn(e,this.array)),this.array[t*this.itemSize]=e,this}getY(t){let e=this.array[t*this.itemSize+1];return this.normalized&&(e=Aa(e,this.array)),e}setY(t,e){return this.normalized&&(e=zn(e,this.array)),this.array[t*this.itemSize+1]=e,this}getZ(t){let e=this.array[t*this.itemSize+2];return this.normalized&&(e=Aa(e,this.array)),e}setZ(t,e){return this.normalized&&(e=zn(e,this.array)),this.array[t*this.itemSize+2]=e,this}getW(t){let e=this.array[t*this.itemSize+3];return this.normalized&&(e=Aa(e,this.array)),e}setW(t,e){return this.normalized&&(e=zn(e,this.array)),this.array[t*this.itemSize+3]=e,this}setXY(t,e,n){return t*=this.itemSize,this.normalized&&(e=zn(e,this.array),n=zn(n,this.array)),this.array[t+0]=e,this.array[t+1]=n,this}setXYZ(t,e,n,i){return t*=this.itemSize,this.normalized&&(e=zn(e,this.array),n=zn(n,this.array),i=zn(i,this.array)),this.array[t+0]=e,this.array[t+1]=n,this.array[t+2]=i,this}setXYZW(t,e,n,i,r){return t*=this.itemSize,this.normalized&&(e=zn(e,this.array),n=zn(n,this.array),i=zn(i,this.array),r=zn(r,this.array)),this.array[t+0]=e,this.array[t+1]=n,this.array[t+2]=i,this.array[t+3]=r,this}onUpload(t){return this.onUploadCallback=t,this}clone(){return new this.constructor(this.array,this.itemSize).copy(this)}toJSON(){let t={itemSize:this.itemSize,type:this.array.constructor.name,array:Array.from(this.array),normalized:this.normalized};return this.name!==""&&(t.name=this.name),this.usage!==Eg&&(t.usage=this.usage),t}};var Cc=class extends ti{constructor(t,e,n){super(new Uint16Array(t),e,n)}};var Rc=class extends ti{constructor(t,e,n){super(new Uint32Array(t),e,n)}};var hn=class extends ti{constructor(t,e,n){super(new Float32Array(t),e,n)}},Ay=0,di=new Ce,Yu=new Hn,fo=new B,Qn=new as,Ia=new as,rn=new B,Ei=class s extends ks{constructor(){super(),this.isBufferGeometry=!0,Object.defineProperty(this,"id",{value:Ay++}),this.uuid=Fo(),this.name="",this.type="BufferGeometry",this.index=null,this.indirect=null,this.attributes={},this.morphAttributes={},this.morphTargetsRelative=!1,this.groups=[],this.boundingBox=null,this.boundingSphere=null,this.drawRange={start:0,count:1/0},this.userData={}}getIndex(){return this.index}setIndex(t){return Array.isArray(t)?this.index=new(H_(t)?Rc:Cc)(t,1):this.index=t,this}setIndirect(t){return this.indirect=t,this}getIndirect(){return this.indirect}getAttribute(t){return this.attributes[t]}setAttribute(t,e){return this.attributes[t]=e,this}deleteAttribute(t){return delete this.attributes[t],this}hasAttribute(t){return this.attributes[t]!==void 0}addGroup(t,e,n=0){this.groups.push({start:t,count:e,materialIndex:n})}clearGroups(){this.groups=[]}setDrawRange(t,e){this.drawRange.start=t,this.drawRange.count=e}applyMatrix4(t){let e=this.attributes.position;e!==void 0&&(e.applyMatrix4(t),e.needsUpdate=!0);let n=this.attributes.normal;if(n!==void 0){let r=new oe().getNormalMatrix(t);n.applyNormalMatrix(r),n.needsUpdate=!0}let i=this.attributes.tangent;return i!==void 0&&(i.transformDirection(t),i.needsUpdate=!0),this.boundingBox!==null&&this.computeBoundingBox(),this.boundingSphere!==null&&this.computeBoundingSphere(),this}applyQuaternion(t){return di.makeRotationFromQuaternion(t),this.applyMatrix4(di),this}rotateX(t){return di.makeRotationX(t),this.applyMatrix4(di),this}rotateY(t){return di.makeRotationY(t),this.applyMatrix4(di),this}rotateZ(t){return di.makeRotationZ(t),this.applyMatrix4(di),this}translate(t,e,n){return di.makeTranslation(t,e,n),this.applyMatrix4(di),this}scale(t,e,n){return di.makeScale(t,e,n),this.applyMatrix4(di),this}lookAt(t){return Yu.lookAt(t),Yu.updateMatrix(),this.applyMatrix4(Yu.matrix),this}center(){return this.computeBoundingBox(),this.boundingBox.getCenter(fo).negate(),this.translate(fo.x,fo.y,fo.z),this}setFromPoints(t){let e=this.getAttribute("position");if(e===void 0){let n=[];for(let i=0,r=t.length;i<r;i++){let o=t[i];n.push(o.x,o.y,o.z||0)}this.setAttribute("position",new hn(n,3))}else{for(let n=0,i=e.count;n<i;n++){let r=t[n];e.setXYZ(n,r.x,r.y,r.z||0)}t.length>e.count&&console.warn("THREE.BufferGeometry: Buffer size too small for points data. Use .dispose() and create a new geometry."),e.needsUpdate=!0}return this}computeBoundingBox(){this.boundingBox===null&&(this.boundingBox=new as);let t=this.attributes.position,e=this.morphAttributes.position;if(t&&t.isGLBufferAttribute){console.error("THREE.BufferGeometry.computeBoundingBox(): GLBufferAttribute requires a manual bounding box.",this),this.boundingBox.set(new B(-1/0,-1/0,-1/0),new B(1/0,1/0,1/0));return}if(t!==void 0){if(this.boundingBox.setFromBufferAttribute(t),e)for(let n=0,i=e.length;n<i;n++){let r=e[n];Qn.setFromBufferAttribute(r),this.morphTargetsRelative?(rn.addVectors(this.boundingBox.min,Qn.min),this.boundingBox.expandByPoint(rn),rn.addVectors(this.boundingBox.max,Qn.max),this.boundingBox.expandByPoint(rn)):(this.boundingBox.expandByPoint(Qn.min),this.boundingBox.expandByPoint(Qn.max))}}else this.boundingBox.makeEmpty();(isNaN(this.boundingBox.min.x)||isNaN(this.boundingBox.min.y)||isNaN(this.boundingBox.min.z))&&console.error('THREE.BufferGeometry.computeBoundingBox(): Computed min/max have NaN values. The "position" attribute is likely to have NaN values.',this)}computeBoundingSphere(){this.boundingSphere===null&&(this.boundingSphere=new Sr);let t=this.attributes.position,e=this.morphAttributes.position;if(t&&t.isGLBufferAttribute){console.error("THREE.BufferGeometry.computeBoundingSphere(): GLBufferAttribute requires a manual bounding sphere.",this),this.boundingSphere.set(new B,1/0);return}if(t){let n=this.boundingSphere.center;if(Qn.setFromBufferAttribute(t),e)for(let r=0,o=e.length;r<o;r++){let a=e[r];Ia.setFromBufferAttribute(a),this.morphTargetsRelative?(rn.addVectors(Qn.min,Ia.min),Qn.expandByPoint(rn),rn.addVectors(Qn.max,Ia.max),Qn.expandByPoint(rn)):(Qn.expandByPoint(Ia.min),Qn.expandByPoint(Ia.max))}Qn.getCenter(n);let i=0;for(let r=0,o=t.count;r<o;r++)rn.fromBufferAttribute(t,r),i=Math.max(i,n.distanceToSquared(rn));if(e)for(let r=0,o=e.length;r<o;r++){let a=e[r],l=this.morphTargetsRelative;for(let c=0,h=a.count;c<h;c++)rn.fromBufferAttribute(a,c),l&&(fo.fromBufferAttribute(t,c),rn.add(fo)),i=Math.max(i,n.distanceToSquared(rn))}this.boundingSphere.radius=Math.sqrt(i),isNaN(this.boundingSphere.radius)&&console.error('THREE.BufferGeometry.computeBoundingSphere(): Computed radius is NaN. The "position" attribute is likely to have NaN values.',this)}}computeTangents(){let t=this.index,e=this.attributes;if(t===null||e.position===void 0||e.normal===void 0||e.uv===void 0){console.error("THREE.BufferGeometry: .computeTangents() failed. Missing required attributes (index, position, normal or uv)");return}let n=e.position,i=e.normal,r=e.uv;this.hasAttribute("tangent")===!1&&this.setAttribute("tangent",new ti(new Float32Array(4*n.count),4));let o=this.getAttribute("tangent"),a=[],l=[];for(let R=0;R<n.count;R++)a[R]=new B,l[R]=new B;let c=new B,h=new B,u=new B,f=new vt,d=new vt,g=new vt,_=new B,m=new B;function p(R,M,x){c.fromBufferAttribute(n,R),h.fromBufferAttribute(n,M),u.fromBufferAttribute(n,x),f.fromBufferAttribute(r,R),d.fromBufferAttribute(r,M),g.fromBufferAttribute(r,x),h.sub(c),u.sub(c),d.sub(f),g.sub(f);let L=1/(d.x*g.y-g.x*d.y);isFinite(L)&&(_.copy(h).multiplyScalar(g.y).addScaledVector(u,-d.y).multiplyScalar(L),m.copy(u).multiplyScalar(d.x).addScaledVector(h,-g.x).multiplyScalar(L),a[R].add(_),a[M].add(_),a[x].add(_),l[R].add(m),l[M].add(m),l[x].add(m))}let S=this.groups;S.length===0&&(S=[{start:0,count:t.count}]);for(let R=0,M=S.length;R<M;++R){let x=S[R],L=x.start,U=x.count;for(let F=L,z=L+U;F<z;F+=3)p(t.getX(F+0),t.getX(F+1),t.getX(F+2))}let y=new B,v=new B,E=new B,A=new B;function T(R){E.fromBufferAttribute(i,R),A.copy(E);let M=a[R];y.copy(M),y.sub(E.multiplyScalar(E.dot(M))).normalize(),v.crossVectors(A,M);let L=v.dot(l[R])<0?-1:1;o.setXYZW(R,y.x,y.y,y.z,L)}for(let R=0,M=S.length;R<M;++R){let x=S[R],L=x.start,U=x.count;for(let F=L,z=L+U;F<z;F+=3)T(t.getX(F+0)),T(t.getX(F+1)),T(t.getX(F+2))}}computeVertexNormals(){let t=this.index,e=this.getAttribute("position");if(e!==void 0){let n=this.getAttribute("normal");if(n===void 0)n=new ti(new Float32Array(e.count*3),3),this.setAttribute("normal",n);else for(let f=0,d=n.count;f<d;f++)n.setXYZ(f,0,0,0);let i=new B,r=new B,o=new B,a=new B,l=new B,c=new B,h=new B,u=new B;if(t)for(let f=0,d=t.count;f<d;f+=3){let g=t.getX(f+0),_=t.getX(f+1),m=t.getX(f+2);i.fromBufferAttribute(e,g),r.fromBufferAttribute(e,_),o.fromBufferAttribute(e,m),h.subVectors(o,r),u.subVectors(i,r),h.cross(u),a.fromBufferAttribute(n,g),l.fromBufferAttribute(n,_),c.fromBufferAttribute(n,m),a.add(h),l.add(h),c.add(h),n.setXYZ(g,a.x,a.y,a.z),n.setXYZ(_,l.x,l.y,l.z),n.setXYZ(m,c.x,c.y,c.z)}else for(let f=0,d=e.count;f<d;f+=3)i.fromBufferAttribute(e,f+0),r.fromBufferAttribute(e,f+1),o.fromBufferAttribute(e,f+2),h.subVectors(o,r),u.subVectors(i,r),h.cross(u),n.setXYZ(f+0,h.x,h.y,h.z),n.setXYZ(f+1,h.x,h.y,h.z),n.setXYZ(f+2,h.x,h.y,h.z);this.normalizeNormals(),n.needsUpdate=!0}}normalizeNormals(){let t=this.attributes.normal;for(let e=0,n=t.count;e<n;e++)rn.fromBufferAttribute(t,e),rn.normalize(),t.setXYZ(e,rn.x,rn.y,rn.z)}toNonIndexed(){function t(a,l){let c=a.array,h=a.itemSize,u=a.normalized,f=new c.constructor(l.length*h),d=0,g=0;for(let _=0,m=l.length;_<m;_++){a.isInterleavedBufferAttribute?d=l[_]*a.data.stride+a.offset:d=l[_]*h;for(let p=0;p<h;p++)f[g++]=c[d++]}return new ti(f,h,u)}if(this.index===null)return console.warn("THREE.BufferGeometry.toNonIndexed(): BufferGeometry is already non-indexed."),this;let e=new s,n=this.index.array,i=this.attributes;for(let a in i){let l=i[a],c=t(l,n);e.setAttribute(a,c)}let r=this.morphAttributes;for(let a in r){let l=[],c=r[a];for(let h=0,u=c.length;h<u;h++){let f=c[h],d=t(f,n);l.push(d)}e.morphAttributes[a]=l}e.morphTargetsRelative=this.morphTargetsRelative;let o=this.groups;for(let a=0,l=o.length;a<l;a++){let c=o[a];e.addGroup(c.start,c.count,c.materialIndex)}return e}toJSON(){let t={metadata:{version:4.6,type:"BufferGeometry",generator:"BufferGeometry.toJSON"}};if(t.uuid=this.uuid,t.type=this.type,this.name!==""&&(t.name=this.name),Object.keys(this.userData).length>0&&(t.userData=this.userData),this.parameters!==void 0){let l=this.parameters;for(let c in l)l[c]!==void 0&&(t[c]=l[c]);return t}t.data={attributes:{}};let e=this.index;e!==null&&(t.data.index={type:e.array.constructor.name,array:Array.prototype.slice.call(e.array)});let n=this.attributes;for(let l in n){let c=n[l];t.data.attributes[l]=c.toJSON(t.data)}let i={},r=!1;for(let l in this.morphAttributes){let c=this.morphAttributes[l],h=[];for(let u=0,f=c.length;u<f;u++){let d=c[u];h.push(d.toJSON(t.data))}h.length>0&&(i[l]=h,r=!0)}r&&(t.data.morphAttributes=i,t.data.morphTargetsRelative=this.morphTargetsRelative);let o=this.groups;o.length>0&&(t.data.groups=JSON.parse(JSON.stringify(o)));let a=this.boundingSphere;return a!==null&&(t.data.boundingSphere={center:a.center.toArray(),radius:a.radius}),t}clone(){return new this.constructor().copy(this)}copy(t){this.index=null,this.attributes={},this.morphAttributes={},this.groups=[],this.boundingBox=null,this.boundingSphere=null;let e={};this.name=t.name;let n=t.index;n!==null&&this.setIndex(n.clone(e));let i=t.attributes;for(let c in i){let h=i[c];this.setAttribute(c,h.clone(e))}let r=t.morphAttributes;for(let c in r){let h=[],u=r[c];for(let f=0,d=u.length;f<d;f++)h.push(u[f].clone(e));this.morphAttributes[c]=h}this.morphTargetsRelative=t.morphTargetsRelative;let o=t.groups;for(let c=0,h=o.length;c<h;c++){let u=o[c];this.addGroup(u.start,u.count,u.materialIndex)}let a=t.boundingBox;a!==null&&(this.boundingBox=a.clone());let l=t.boundingSphere;return l!==null&&(this.boundingSphere=l.clone()),this.drawRange.start=t.drawRange.start,this.drawRange.count=t.drawRange.count,this.userData=t.userData,this}dispose(){this.dispatchEvent({type:"dispose"})}},Gg=new Ce,ur=new Kf,tc=new Sr,Wg=new B,ec=new B,nc=new B,ic=new B,qu=new B,sc=new B,Xg=new B,rc=new B,ve=class extends Hn{constructor(t=new Ei,e=new Ti){super(),this.isMesh=!0,this.type="Mesh",this.geometry=t,this.material=e,this.updateMorphTargets()}copy(t,e){return super.copy(t,e),t.morphTargetInfluences!==void 0&&(this.morphTargetInfluences=t.morphTargetInfluences.slice()),t.morphTargetDictionary!==void 0&&(this.morphTargetDictionary=Object.assign({},t.morphTargetDictionary)),this.material=Array.isArray(t.material)?t.material.slice():t.material,this.geometry=t.geometry,this}updateMorphTargets(){let e=this.geometry.morphAttributes,n=Object.keys(e);if(n.length>0){let i=e[n[0]];if(i!==void 0){this.morphTargetInfluences=[],this.morphTargetDictionary={};for(let r=0,o=i.length;r<o;r++){let a=i[r].name||String(r);this.morphTargetInfluences.push(0),this.morphTargetDictionary[a]=r}}}}getVertexPosition(t,e){let n=this.geometry,i=n.attributes.position,r=n.morphAttributes.position,o=n.morphTargetsRelative;e.fromBufferAttribute(i,t);let a=this.morphTargetInfluences;if(r&&a){sc.set(0,0,0);for(let l=0,c=r.length;l<c;l++){let h=a[l],u=r[l];h!==0&&(qu.fromBufferAttribute(u,t),o?sc.addScaledVector(qu,h):sc.addScaledVector(qu.sub(e),h))}e.add(sc)}return e}raycast(t,e){let n=this.geometry,i=this.material,r=this.matrixWorld;i!==void 0&&(n.boundingSphere===null&&n.computeBoundingSphere(),tc.copy(n.boundingSphere),tc.applyMatrix4(r),ur.copy(t.ray).recast(t.near),!(tc.containsPoint(ur.origin)===!1&&(ur.intersectSphere(tc,Wg)===null||ur.origin.distanceToSquared(Wg)>(t.far-t.near)**2))&&(Gg.copy(r).invert(),ur.copy(t.ray).applyMatrix4(Gg),!(n.boundingBox!==null&&ur.intersectsBox(n.boundingBox)===!1)&&this._computeIntersections(t,e,ur)))}_computeIntersections(t,e,n){let i,r=this.geometry,o=this.material,a=r.index,l=r.attributes.position,c=r.attributes.uv,h=r.attributes.uv1,u=r.attributes.normal,f=r.groups,d=r.drawRange;if(a!==null)if(Array.isArray(o))for(let g=0,_=f.length;g<_;g++){let m=f[g],p=o[m.materialIndex],S=Math.max(m.start,d.start),y=Math.min(a.count,Math.min(m.start+m.count,d.start+d.count));for(let v=S,E=y;v<E;v+=3){let A=a.getX(v),T=a.getX(v+1),R=a.getX(v+2);i=oc(this,p,t,n,c,h,u,A,T,R),i&&(i.faceIndex=Math.floor(v/3),i.face.materialIndex=m.materialIndex,e.push(i))}}else{let g=Math.max(0,d.start),_=Math.min(a.count,d.start+d.count);for(let m=g,p=_;m<p;m+=3){let S=a.getX(m),y=a.getX(m+1),v=a.getX(m+2);i=oc(this,o,t,n,c,h,u,S,y,v),i&&(i.faceIndex=Math.floor(m/3),e.push(i))}}else if(l!==void 0)if(Array.isArray(o))for(let g=0,_=f.length;g<_;g++){let m=f[g],p=o[m.materialIndex],S=Math.max(m.start,d.start),y=Math.min(l.count,Math.min(m.start+m.count,d.start+d.count));for(let v=S,E=y;v<E;v+=3){let A=v,T=v+1,R=v+2;i=oc(this,p,t,n,c,h,u,A,T,R),i&&(i.faceIndex=Math.floor(v/3),i.face.materialIndex=m.materialIndex,e.push(i))}}else{let g=Math.max(0,d.start),_=Math.min(l.count,d.start+d.count);for(let m=g,p=_;m<p;m+=3){let S=m,y=m+1,v=m+2;i=oc(this,o,t,n,c,h,u,S,y,v),i&&(i.faceIndex=Math.floor(m/3),e.push(i))}}}};function Cy(s,t,e,n,i,r,o,a){let l;if(t.side===wn?l=n.intersectTriangle(o,r,i,!0,a):l=n.intersectTriangle(i,r,o,t.side===Bs,a),l===null)return null;rc.copy(a),rc.applyMatrix4(s.matrixWorld);let c=e.ray.origin.distanceTo(rc);return c<e.near||c>e.far?null:{distance:c,point:rc.clone(),object:s}}function oc(s,t,e,n,i,r,o,a,l,c){s.getVertexPosition(a,ec),s.getVertexPosition(l,nc),s.getVertexPosition(c,ic);let h=Cy(s,t,e,n,ec,nc,ic,Xg);if(h){let u=new B;_r.getBarycoord(Xg,ec,nc,ic,u),i&&(h.uv=_r.getInterpolatedAttribute(i,a,l,c,u,new vt)),r&&(h.uv1=_r.getInterpolatedAttribute(r,a,l,c,u,new vt)),o&&(h.normal=_r.getInterpolatedAttribute(o,a,l,c,u,new B),h.normal.dot(n.direction)>0&&h.normal.multiplyScalar(-1));let f={a,b:l,c,normal:new B,materialIndex:0};_r.getNormal(ec,nc,ic,f.normal),h.face=f,h.barycoord=u}return h}var wr=class s extends Ei{constructor(t=1,e=1,n=1,i=1,r=1,o=1){super(),this.type="BoxGeometry",this.parameters={width:t,height:e,depth:n,widthSegments:i,heightSegments:r,depthSegments:o};let a=this;i=Math.floor(i),r=Math.floor(r),o=Math.floor(o);let l=[],c=[],h=[],u=[],f=0,d=0;g("z","y","x",-1,-1,n,e,t,o,r,0),g("z","y","x",1,-1,n,e,-t,o,r,1),g("x","z","y",1,1,t,n,e,i,o,2),g("x","z","y",1,-1,t,n,-e,i,o,3),g("x","y","z",1,-1,t,e,n,i,r,4),g("x","y","z",-1,-1,t,e,-n,i,r,5),this.setIndex(l),this.setAttribute("position",new hn(c,3)),this.setAttribute("normal",new hn(h,3)),this.setAttribute("uv",new hn(u,2));function g(_,m,p,S,y,v,E,A,T,R,M){let x=v/T,L=E/R,U=v/2,F=E/2,z=A/2,q=T+1,H=R+1,W=0,V=0,st=new B;for(let I=0;I<H;I++){let at=I*L-F;for(let Dt=0;Dt<q;Dt++){let Vt=Dt*x-U;st[_]=Vt*S,st[m]=at*y,st[p]=z,c.push(st.x,st.y,st.z),st[_]=0,st[m]=0,st[p]=A>0?1:-1,h.push(st.x,st.y,st.z),u.push(Dt/T),u.push(1-I/R),W+=1}}for(let I=0;I<R;I++)for(let at=0;at<T;at++){let Dt=f+at+q*I,Vt=f+at+q*(I+1),Z=f+(at+1)+q*(I+1),rt=f+(at+1)+q*I;l.push(Dt,Vt,rt),l.push(Vt,Z,rt),V+=6}a.addGroup(d,V,M),d+=V,f+=W}}copy(t){return super.copy(t),this.parameters=Object.assign({},t.parameters),this}static fromJSON(t){return new s(t.width,t.height,t.depth,t.widthSegments,t.heightSegments,t.depthSegments)}};function Ro(s){let t={};for(let e in s){t[e]={};for(let n in s[e]){let i=s[e][n];i&&(i.isColor||i.isMatrix3||i.isMatrix4||i.isVector2||i.isVector3||i.isVector4||i.isTexture||i.isQuaternion)?i.isRenderTargetTexture?(console.warn("UniformsUtils: Textures of render targets cannot be cloned via cloneUniforms() or mergeUniforms()."),t[e][n]=null):t[e][n]=i.clone():Array.isArray(i)?t[e][n]=i.slice():t[e][n]=i}}return t}function Dn(s){let t={};for(let e=0;e<s.length;e++){let n=Ro(s[e]);for(let i in n)t[i]=n[i]}return t}function Ry(s){let t=[];for(let e=0;e<s.length;e++)t.push(s[e].clone());return t}function W_(s){let t=s.getRenderTarget();return t===null?s.outputColorSpace:t.isXRRenderTarget===!0?t.texture.colorSpace:ge.workingColorSpace}var zs={clone:Ro,merge:Dn},Py=`void main() {
	gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
}`,Iy=`void main() {
	gl_FragColor = vec4( 1.0, 0.0, 0.0, 1.0 );
}`,je=class extends br{static get type(){return"ShaderMaterial"}constructor(t){super(),this.isShaderMaterial=!0,this.defines={},this.uniforms={},this.uniformsGroups=[],this.vertexShader=Py,this.fragmentShader=Iy,this.linewidth=1,this.wireframe=!1,this.wireframeLinewidth=1,this.fog=!1,this.lights=!1,this.clipping=!1,this.forceSinglePass=!0,this.extensions={clipCullDistance:!1,multiDraw:!1},this.defaultAttributeValues={color:[1,1,1],uv:[0,0],uv1:[0,0]},this.index0AttributeName=void 0,this.uniformsNeedUpdate=!1,this.glslVersion=null,t!==void 0&&this.setValues(t)}copy(t){return super.copy(t),this.fragmentShader=t.fragmentShader,this.vertexShader=t.vertexShader,this.uniforms=Ro(t.uniforms),this.uniformsGroups=Ry(t.uniformsGroups),this.defines=Object.assign({},t.defines),this.wireframe=t.wireframe,this.wireframeLinewidth=t.wireframeLinewidth,this.fog=t.fog,this.lights=t.lights,this.clipping=t.clipping,this.extensions=Object.assign({},t.extensions),this.glslVersion=t.glslVersion,this}toJSON(t){let e=super.toJSON(t);e.glslVersion=this.glslVersion,e.uniforms={};for(let i in this.uniforms){let o=this.uniforms[i].value;o&&o.isTexture?e.uniforms[i]={type:"t",value:o.toJSON(t).uuid}:o&&o.isColor?e.uniforms[i]={type:"c",value:o.getHex()}:o&&o.isVector2?e.uniforms[i]={type:"v2",value:o.toArray()}:o&&o.isVector3?e.uniforms[i]={type:"v3",value:o.toArray()}:o&&o.isVector4?e.uniforms[i]={type:"v4",value:o.toArray()}:o&&o.isMatrix3?e.uniforms[i]={type:"m3",value:o.toArray()}:o&&o.isMatrix4?e.uniforms[i]={type:"m4",value:o.toArray()}:e.uniforms[i]={value:o}}Object.keys(this.defines).length>0&&(e.defines=this.defines),e.vertexShader=this.vertexShader,e.fragmentShader=this.fragmentShader,e.lights=this.lights,e.clipping=this.clipping;let n={};for(let i in this.extensions)this.extensions[i]===!0&&(n[i]=!0);return Object.keys(n).length>0&&(e.extensions=n),e}},Pc=class extends Hn{constructor(){super(),this.isCamera=!0,this.type="Camera",this.matrixWorldInverse=new Ce,this.projectionMatrix=new Ce,this.projectionMatrixInverse=new Ce,this.coordinateSystem=ss}copy(t,e){return super.copy(t,e),this.matrixWorldInverse.copy(t.matrixWorldInverse),this.projectionMatrix.copy(t.projectionMatrix),this.projectionMatrixInverse.copy(t.projectionMatrixInverse),this.coordinateSystem=t.coordinateSystem,this}getWorldDirection(t){return super.getWorldDirection(t).negate()}updateMatrixWorld(t){super.updateMatrixWorld(t),this.matrixWorldInverse.copy(this.matrixWorld).invert()}updateWorldMatrix(t,e){super.updateWorldMatrix(t,e),this.matrixWorldInverse.copy(this.matrixWorld).invert()}clone(){return new this.constructor().copy(this)}},Ds=new B,Yg=new vt,qg=new vt,bn=class extends Pc{constructor(t=50,e=1,n=.1,i=2e3){super(),this.isPerspectiveCamera=!0,this.type="PerspectiveCamera",this.fov=t,this.zoom=1,this.near=n,this.far=i,this.focus=10,this.aspect=e,this.view=null,this.filmGauge=35,this.filmOffset=0,this.updateProjectionMatrix()}copy(t,e){return super.copy(t,e),this.fov=t.fov,this.zoom=t.zoom,this.near=t.near,this.far=t.far,this.focus=t.focus,this.aspect=t.aspect,this.view=t.view===null?null:Object.assign({},t.view),this.filmGauge=t.filmGauge,this.filmOffset=t.filmOffset,this}setFocalLength(t){let e=.5*this.getFilmHeight()/t;this.fov=qf*2*Math.atan(e),this.updateProjectionMatrix()}getFocalLength(){let t=Math.tan(Au*.5*this.fov);return .5*this.getFilmHeight()/t}getEffectiveFOV(){return qf*2*Math.atan(Math.tan(Au*.5*this.fov)/this.zoom)}getFilmWidth(){return this.filmGauge*Math.min(this.aspect,1)}getFilmHeight(){return this.filmGauge/Math.max(this.aspect,1)}getViewBounds(t,e,n){Ds.set(-1,-1,.5).applyMatrix4(this.projectionMatrixInverse),e.set(Ds.x,Ds.y).multiplyScalar(-t/Ds.z),Ds.set(1,1,.5).applyMatrix4(this.projectionMatrixInverse),n.set(Ds.x,Ds.y).multiplyScalar(-t/Ds.z)}getViewSize(t,e){return this.getViewBounds(t,Yg,qg),e.subVectors(qg,Yg)}setViewOffset(t,e,n,i,r,o){this.aspect=t/e,this.view===null&&(this.view={enabled:!0,fullWidth:1,fullHeight:1,offsetX:0,offsetY:0,width:1,height:1}),this.view.enabled=!0,this.view.fullWidth=t,this.view.fullHeight=e,this.view.offsetX=n,this.view.offsetY=i,this.view.width=r,this.view.height=o,this.updateProjectionMatrix()}clearViewOffset(){this.view!==null&&(this.view.enabled=!1),this.updateProjectionMatrix()}updateProjectionMatrix(){let t=this.near,e=t*Math.tan(Au*.5*this.fov)/this.zoom,n=2*e,i=this.aspect*n,r=-.5*i,o=this.view;if(this.view!==null&&this.view.enabled){let l=o.fullWidth,c=o.fullHeight;r+=o.offsetX*i/l,e-=o.offsetY*n/c,i*=o.width/l,n*=o.height/c}let a=this.filmOffset;a!==0&&(r+=t*a/this.getFilmWidth()),this.projectionMatrix.makePerspective(r,r+i,e,e-n,t,this.far,this.coordinateSystem),this.projectionMatrixInverse.copy(this.projectionMatrix).invert()}toJSON(t){let e=super.toJSON(t);return e.object.fov=this.fov,e.object.zoom=this.zoom,e.object.near=this.near,e.object.far=this.far,e.object.focus=this.focus,e.object.aspect=this.aspect,this.view!==null&&(e.object.view=Object.assign({},this.view)),e.object.filmGauge=this.filmGauge,e.object.filmOffset=this.filmOffset,e}},po=-90,mo=1,Qf=class extends Hn{constructor(t,e,n){super(),this.type="CubeCamera",this.renderTarget=n,this.coordinateSystem=null,this.activeMipmapLevel=0;let i=new bn(po,mo,t,e);i.layers=this.layers,this.add(i);let r=new bn(po,mo,t,e);r.layers=this.layers,this.add(r);let o=new bn(po,mo,t,e);o.layers=this.layers,this.add(o);let a=new bn(po,mo,t,e);a.layers=this.layers,this.add(a);let l=new bn(po,mo,t,e);l.layers=this.layers,this.add(l);let c=new bn(po,mo,t,e);c.layers=this.layers,this.add(c)}updateCoordinateSystem(){let t=this.coordinateSystem,e=this.children.concat(),[n,i,r,o,a,l]=e;for(let c of e)this.remove(c);if(t===ss)n.up.set(0,1,0),n.lookAt(1,0,0),i.up.set(0,1,0),i.lookAt(-1,0,0),r.up.set(0,0,-1),r.lookAt(0,1,0),o.up.set(0,0,1),o.lookAt(0,-1,0),a.up.set(0,1,0),a.lookAt(0,0,1),l.up.set(0,1,0),l.lookAt(0,0,-1);else if(t===bc)n.up.set(0,-1,0),n.lookAt(-1,0,0),i.up.set(0,-1,0),i.lookAt(1,0,0),r.up.set(0,0,1),r.lookAt(0,1,0),o.up.set(0,0,-1),o.lookAt(0,-1,0),a.up.set(0,-1,0),a.lookAt(0,0,1),l.up.set(0,-1,0),l.lookAt(0,0,-1);else throw new Error("THREE.CubeCamera.updateCoordinateSystem(): Invalid coordinate system: "+t);for(let c of e)this.add(c),c.updateMatrixWorld()}update(t,e){this.parent===null&&this.updateMatrixWorld();let{renderTarget:n,activeMipmapLevel:i}=this;this.coordinateSystem!==t.coordinateSystem&&(this.coordinateSystem=t.coordinateSystem,this.updateCoordinateSystem());let[r,o,a,l,c,h]=this.children,u=t.getRenderTarget(),f=t.getActiveCubeFace(),d=t.getActiveMipmapLevel(),g=t.xr.enabled;t.xr.enabled=!1;let _=n.texture.generateMipmaps;n.texture.generateMipmaps=!1,t.setRenderTarget(n,0,i),t.render(e,r),t.setRenderTarget(n,1,i),t.render(e,o),t.setRenderTarget(n,2,i),t.render(e,a),t.setRenderTarget(n,3,i),t.render(e,l),t.setRenderTarget(n,4,i),t.render(e,c),n.texture.generateMipmaps=_,t.setRenderTarget(n,5,i),t.render(e,h),t.setRenderTarget(u,f,d),t.xr.enabled=g,n.texture.needsPMREMUpdate=!0}},Ic=class extends Vn{constructor(t,e,n,i,r,o,a,l,c,h){t=t!==void 0?t:[],e=e!==void 0?e:To,super(t,e,n,i,r,o,a,l,c,h),this.isCubeTexture=!0,this.flipY=!1}get images(){return this.image}set images(t){this.image=t}},jf=class extends un{constructor(t=1,e={}){super(t,t,e),this.isWebGLCubeRenderTarget=!0;let n={width:t,height:t,depth:1},i=[n,n,n,n,n,n];this.texture=new Ic(i,e.mapping,e.wrapS,e.wrapT,e.magFilter,e.minFilter,e.format,e.type,e.anisotropy,e.colorSpace),this.texture.isRenderTargetTexture=!0,this.texture.generateMipmaps=e.generateMipmaps!==void 0?e.generateMipmaps:!1,this.texture.minFilter=e.minFilter!==void 0?e.minFilter:Fi}fromEquirectangularTexture(t,e){this.texture.type=e.type,this.texture.colorSpace=e.colorSpace,this.texture.generateMipmaps=e.generateMipmaps,this.texture.minFilter=e.minFilter,this.texture.magFilter=e.magFilter;let n={uniforms:{tEquirect:{value:null}},vertexShader:`

				varying vec3 vWorldDirection;

				vec3 transformDirection( in vec3 dir, in mat4 matrix ) {

					return normalize( ( matrix * vec4( dir, 0.0 ) ).xyz );

				}

				void main() {

					vWorldDirection = transformDirection( position, modelMatrix );

					#include <begin_vertex>
					#include <project_vertex>

				}
			`,fragmentShader:`

				uniform sampler2D tEquirect;

				varying vec3 vWorldDirection;

				#include <common>

				void main() {

					vec3 direction = normalize( vWorldDirection );

					vec2 sampleUV = equirectUv( direction );

					gl_FragColor = texture2D( tEquirect, sampleUV );

				}
			`},i=new wr(5,5,5),r=new je({name:"CubemapFromEquirect",uniforms:Ro(n.uniforms),vertexShader:n.vertexShader,fragmentShader:n.fragmentShader,side:wn,blending:ki});r.uniforms.tEquirect.value=e;let o=new ve(i,r),a=e.minFilter;return e.minFilter===yr&&(e.minFilter=Fi),new Qf(1,10,this).update(t,o),e.minFilter=a,o.geometry.dispose(),o.material.dispose(),this}clear(t,e,n,i){let r=t.getRenderTarget();for(let o=0;o<6;o++)t.setRenderTarget(this,o),t.clear(e,n,i);t.setRenderTarget(r)}},Zu=new B,Ly=new B,Dy=new oe,is=class{constructor(t=new B(1,0,0),e=0){this.isPlane=!0,this.normal=t,this.constant=e}set(t,e){return this.normal.copy(t),this.constant=e,this}setComponents(t,e,n,i){return this.normal.set(t,e,n),this.constant=i,this}setFromNormalAndCoplanarPoint(t,e){return this.normal.copy(t),this.constant=-e.dot(this.normal),this}setFromCoplanarPoints(t,e,n){let i=Zu.subVectors(n,e).cross(Ly.subVectors(t,e)).normalize();return this.setFromNormalAndCoplanarPoint(i,t),this}copy(t){return this.normal.copy(t.normal),this.constant=t.constant,this}normalize(){let t=1/this.normal.length();return this.normal.multiplyScalar(t),this.constant*=t,this}negate(){return this.constant*=-1,this.normal.negate(),this}distanceToPoint(t){return this.normal.dot(t)+this.constant}distanceToSphere(t){return this.distanceToPoint(t.center)-t.radius}projectPoint(t,e){return e.copy(t).addScaledVector(this.normal,-this.distanceToPoint(t))}intersectLine(t,e){let n=t.delta(Zu),i=this.normal.dot(n);if(i===0)return this.distanceToPoint(t.start)===0?e.copy(t.start):null;let r=-(t.start.dot(this.normal)+this.constant)/i;return r<0||r>1?null:e.copy(t.start).addScaledVector(n,r)}intersectsLine(t){let e=this.distanceToPoint(t.start),n=this.distanceToPoint(t.end);return e<0&&n>0||n<0&&e>0}intersectsBox(t){return t.intersectsPlane(this)}intersectsSphere(t){return t.intersectsPlane(this)}coplanarPoint(t){return t.copy(this.normal).multiplyScalar(-this.constant)}applyMatrix4(t,e){let n=e||Dy.getNormalMatrix(t),i=this.coplanarPoint(Zu).applyMatrix4(t),r=this.normal.applyMatrix3(n).normalize();return this.constant=-i.dot(r),this}translate(t){return this.constant-=t.dot(this.normal),this}equals(t){return t.normal.equals(this.normal)&&t.constant===this.constant}clone(){return new this.constructor().copy(this)}},fr=new Sr,ac=new B,Va=class{constructor(t=new is,e=new is,n=new is,i=new is,r=new is,o=new is){this.planes=[t,e,n,i,r,o]}set(t,e,n,i,r,o){let a=this.planes;return a[0].copy(t),a[1].copy(e),a[2].copy(n),a[3].copy(i),a[4].copy(r),a[5].copy(o),this}copy(t){let e=this.planes;for(let n=0;n<6;n++)e[n].copy(t.planes[n]);return this}setFromProjectionMatrix(t,e=ss){let n=this.planes,i=t.elements,r=i[0],o=i[1],a=i[2],l=i[3],c=i[4],h=i[5],u=i[6],f=i[7],d=i[8],g=i[9],_=i[10],m=i[11],p=i[12],S=i[13],y=i[14],v=i[15];if(n[0].setComponents(l-r,f-c,m-d,v-p).normalize(),n[1].setComponents(l+r,f+c,m+d,v+p).normalize(),n[2].setComponents(l+o,f+h,m+g,v+S).normalize(),n[3].setComponents(l-o,f-h,m-g,v-S).normalize(),n[4].setComponents(l-a,f-u,m-_,v-y).normalize(),e===ss)n[5].setComponents(l+a,f+u,m+_,v+y).normalize();else if(e===bc)n[5].setComponents(a,u,_,y).normalize();else throw new Error("THREE.Frustum.setFromProjectionMatrix(): Invalid coordinate system: "+e);return this}intersectsObject(t){if(t.boundingSphere!==void 0)t.boundingSphere===null&&t.computeBoundingSphere(),fr.copy(t.boundingSphere).applyMatrix4(t.matrixWorld);else{let e=t.geometry;e.boundingSphere===null&&e.computeBoundingSphere(),fr.copy(e.boundingSphere).applyMatrix4(t.matrixWorld)}return this.intersectsSphere(fr)}intersectsSprite(t){return fr.center.set(0,0,0),fr.radius=.7071067811865476,fr.applyMatrix4(t.matrixWorld),this.intersectsSphere(fr)}intersectsSphere(t){let e=this.planes,n=t.center,i=-t.radius;for(let r=0;r<6;r++)if(e[r].distanceToPoint(n)<i)return!1;return!0}intersectsBox(t){let e=this.planes;for(let n=0;n<6;n++){let i=e[n];if(ac.x=i.normal.x>0?t.max.x:t.min.x,ac.y=i.normal.y>0?t.max.y:t.min.y,ac.z=i.normal.z>0?t.max.z:t.min.z,i.distanceToPoint(ac)<0)return!1}return!0}containsPoint(t){let e=this.planes;for(let n=0;n<6;n++)if(e[n].distanceToPoint(t)<0)return!1;return!0}clone(){return new this.constructor().copy(this)}};function X_(){let s=null,t=!1,e=null,n=null;function i(r,o){e(r,o),n=s.requestAnimationFrame(i)}return{start:function(){t!==!0&&e!==null&&(n=s.requestAnimationFrame(i),t=!0)},stop:function(){s.cancelAnimationFrame(n),t=!1},setAnimationLoop:function(r){e=r},setContext:function(r){s=r}}}function Uy(s){let t=new WeakMap;function e(a,l){let c=a.array,h=a.usage,u=c.byteLength,f=s.createBuffer();s.bindBuffer(l,f),s.bufferData(l,c,h),a.onUploadCallback();let d;if(c instanceof Float32Array)d=s.FLOAT;else if(c instanceof Uint16Array)a.isFloat16BufferAttribute?d=s.HALF_FLOAT:d=s.UNSIGNED_SHORT;else if(c instanceof Int16Array)d=s.SHORT;else if(c instanceof Uint32Array)d=s.UNSIGNED_INT;else if(c instanceof Int32Array)d=s.INT;else if(c instanceof Int8Array)d=s.BYTE;else if(c instanceof Uint8Array)d=s.UNSIGNED_BYTE;else if(c instanceof Uint8ClampedArray)d=s.UNSIGNED_BYTE;else throw new Error("THREE.WebGLAttributes: Unsupported buffer data format: "+c);return{buffer:f,type:d,bytesPerElement:c.BYTES_PER_ELEMENT,version:a.version,size:u}}function n(a,l,c){let h=l.array,u=l.updateRanges;if(s.bindBuffer(c,a),u.length===0)s.bufferSubData(c,0,h);else{u.sort((d,g)=>d.start-g.start);let f=0;for(let d=1;d<u.length;d++){let g=u[f],_=u[d];_.start<=g.start+g.count+1?g.count=Math.max(g.count,_.start+_.count-g.start):(++f,u[f]=_)}u.length=f+1;for(let d=0,g=u.length;d<g;d++){let _=u[d];s.bufferSubData(c,_.start*h.BYTES_PER_ELEMENT,h,_.start,_.count)}l.clearUpdateRanges()}l.onUploadCallback()}function i(a){return a.isInterleavedBufferAttribute&&(a=a.data),t.get(a)}function r(a){a.isInterleavedBufferAttribute&&(a=a.data);let l=t.get(a);l&&(s.deleteBuffer(l.buffer),t.delete(a))}function o(a,l){if(a.isInterleavedBufferAttribute&&(a=a.data),a.isGLBufferAttribute){let h=t.get(a);(!h||h.version<a.version)&&t.set(a,{buffer:a.buffer,type:a.type,bytesPerElement:a.elementSize,version:a.version});return}let c=t.get(a);if(c===void 0)t.set(a,e(a,l));else if(c.version<a.version){if(c.size!==a.array.byteLength)throw new Error("THREE.WebGLAttributes: The size of the buffer attribute's array buffer does not match the original size. Resizing buffer attributes is not supported.");n(c.buffer,a,l),c.version=a.version}}return{get:i,remove:r,update:o}}var Tr=class s extends Ei{constructor(t=1,e=1,n=1,i=1){super(),this.type="PlaneGeometry",this.parameters={width:t,height:e,widthSegments:n,heightSegments:i};let r=t/2,o=e/2,a=Math.floor(n),l=Math.floor(i),c=a+1,h=l+1,u=t/a,f=e/l,d=[],g=[],_=[],m=[];for(let p=0;p<h;p++){let S=p*f-o;for(let y=0;y<c;y++){let v=y*u-r;g.push(v,-S,0),_.push(0,0,1),m.push(y/a),m.push(1-p/l)}}for(let p=0;p<l;p++)for(let S=0;S<a;S++){let y=S+c*p,v=S+c*(p+1),E=S+1+c*(p+1),A=S+1+c*p;d.push(y,v,A),d.push(v,E,A)}this.setIndex(d),this.setAttribute("position",new hn(g,3)),this.setAttribute("normal",new hn(_,3)),this.setAttribute("uv",new hn(m,2))}copy(t){return super.copy(t),this.parameters=Object.assign({},t.parameters),this}static fromJSON(t){return new s(t.width,t.height,t.widthSegments,t.heightSegments)}},Ny=`#ifdef USE_ALPHAHASH
	if ( diffuseColor.a < getAlphaHashThreshold( vPosition ) ) discard;
#endif`,Oy=`#ifdef USE_ALPHAHASH
	const float ALPHA_HASH_SCALE = 0.05;
	float hash2D( vec2 value ) {
		return fract( 1.0e4 * sin( 17.0 * value.x + 0.1 * value.y ) * ( 0.1 + abs( sin( 13.0 * value.y + value.x ) ) ) );
	}
	float hash3D( vec3 value ) {
		return hash2D( vec2( hash2D( value.xy ), value.z ) );
	}
	float getAlphaHashThreshold( vec3 position ) {
		float maxDeriv = max(
			length( dFdx( position.xyz ) ),
			length( dFdy( position.xyz ) )
		);
		float pixScale = 1.0 / ( ALPHA_HASH_SCALE * maxDeriv );
		vec2 pixScales = vec2(
			exp2( floor( log2( pixScale ) ) ),
			exp2( ceil( log2( pixScale ) ) )
		);
		vec2 alpha = vec2(
			hash3D( floor( pixScales.x * position.xyz ) ),
			hash3D( floor( pixScales.y * position.xyz ) )
		);
		float lerpFactor = fract( log2( pixScale ) );
		float x = ( 1.0 - lerpFactor ) * alpha.x + lerpFactor * alpha.y;
		float a = min( lerpFactor, 1.0 - lerpFactor );
		vec3 cases = vec3(
			x * x / ( 2.0 * a * ( 1.0 - a ) ),
			( x - 0.5 * a ) / ( 1.0 - a ),
			1.0 - ( ( 1.0 - x ) * ( 1.0 - x ) / ( 2.0 * a * ( 1.0 - a ) ) )
		);
		float threshold = ( x < ( 1.0 - a ) )
			? ( ( x < a ) ? cases.x : cases.y )
			: cases.z;
		return clamp( threshold , 1.0e-6, 1.0 );
	}
#endif`,Fy=`#ifdef USE_ALPHAMAP
	diffuseColor.a *= texture2D( alphaMap, vAlphaMapUv ).g;
#endif`,By=`#ifdef USE_ALPHAMAP
	uniform sampler2D alphaMap;
#endif`,ky=`#ifdef USE_ALPHATEST
	#ifdef ALPHA_TO_COVERAGE
	diffuseColor.a = smoothstep( alphaTest, alphaTest + fwidth( diffuseColor.a ), diffuseColor.a );
	if ( diffuseColor.a == 0.0 ) discard;
	#else
	if ( diffuseColor.a < alphaTest ) discard;
	#endif
#endif`,zy=`#ifdef USE_ALPHATEST
	uniform float alphaTest;
#endif`,Vy=`#ifdef USE_AOMAP
	float ambientOcclusion = ( texture2D( aoMap, vAoMapUv ).r - 1.0 ) * aoMapIntensity + 1.0;
	reflectedLight.indirectDiffuse *= ambientOcclusion;
	#if defined( USE_CLEARCOAT ) 
		clearcoatSpecularIndirect *= ambientOcclusion;
	#endif
	#if defined( USE_SHEEN ) 
		sheenSpecularIndirect *= ambientOcclusion;
	#endif
	#if defined( USE_ENVMAP ) && defined( STANDARD )
		float dotNV = saturate( dot( geometryNormal, geometryViewDir ) );
		reflectedLight.indirectSpecular *= computeSpecularOcclusion( dotNV, ambientOcclusion, material.roughness );
	#endif
#endif`,Hy=`#ifdef USE_AOMAP
	uniform sampler2D aoMap;
	uniform float aoMapIntensity;
#endif`,Gy=`#ifdef USE_BATCHING
	#if ! defined( GL_ANGLE_multi_draw )
	#define gl_DrawID _gl_DrawID
	uniform int _gl_DrawID;
	#endif
	uniform highp sampler2D batchingTexture;
	uniform highp usampler2D batchingIdTexture;
	mat4 getBatchingMatrix( const in float i ) {
		int size = textureSize( batchingTexture, 0 ).x;
		int j = int( i ) * 4;
		int x = j % size;
		int y = j / size;
		vec4 v1 = texelFetch( batchingTexture, ivec2( x, y ), 0 );
		vec4 v2 = texelFetch( batchingTexture, ivec2( x + 1, y ), 0 );
		vec4 v3 = texelFetch( batchingTexture, ivec2( x + 2, y ), 0 );
		vec4 v4 = texelFetch( batchingTexture, ivec2( x + 3, y ), 0 );
		return mat4( v1, v2, v3, v4 );
	}
	float getIndirectIndex( const in int i ) {
		int size = textureSize( batchingIdTexture, 0 ).x;
		int x = i % size;
		int y = i / size;
		return float( texelFetch( batchingIdTexture, ivec2( x, y ), 0 ).r );
	}
#endif
#ifdef USE_BATCHING_COLOR
	uniform sampler2D batchingColorTexture;
	vec3 getBatchingColor( const in float i ) {
		int size = textureSize( batchingColorTexture, 0 ).x;
		int j = int( i );
		int x = j % size;
		int y = j / size;
		return texelFetch( batchingColorTexture, ivec2( x, y ), 0 ).rgb;
	}
#endif`,Wy=`#ifdef USE_BATCHING
	mat4 batchingMatrix = getBatchingMatrix( getIndirectIndex( gl_DrawID ) );
#endif`,Xy=`vec3 transformed = vec3( position );
#ifdef USE_ALPHAHASH
	vPosition = vec3( position );
#endif`,Yy=`vec3 objectNormal = vec3( normal );
#ifdef USE_TANGENT
	vec3 objectTangent = vec3( tangent.xyz );
#endif`,qy=`float G_BlinnPhong_Implicit( ) {
	return 0.25;
}
float D_BlinnPhong( const in float shininess, const in float dotNH ) {
	return RECIPROCAL_PI * ( shininess * 0.5 + 1.0 ) * pow( dotNH, shininess );
}
vec3 BRDF_BlinnPhong( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in vec3 specularColor, const in float shininess ) {
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNH = saturate( dot( normal, halfDir ) );
	float dotVH = saturate( dot( viewDir, halfDir ) );
	vec3 F = F_Schlick( specularColor, 1.0, dotVH );
	float G = G_BlinnPhong_Implicit( );
	float D = D_BlinnPhong( shininess, dotNH );
	return F * ( G * D );
} // validated`,Zy=`#ifdef USE_IRIDESCENCE
	const mat3 XYZ_TO_REC709 = mat3(
		 3.2404542, -0.9692660,  0.0556434,
		-1.5371385,  1.8760108, -0.2040259,
		-0.4985314,  0.0415560,  1.0572252
	);
	vec3 Fresnel0ToIor( vec3 fresnel0 ) {
		vec3 sqrtF0 = sqrt( fresnel0 );
		return ( vec3( 1.0 ) + sqrtF0 ) / ( vec3( 1.0 ) - sqrtF0 );
	}
	vec3 IorToFresnel0( vec3 transmittedIor, float incidentIor ) {
		return pow2( ( transmittedIor - vec3( incidentIor ) ) / ( transmittedIor + vec3( incidentIor ) ) );
	}
	float IorToFresnel0( float transmittedIor, float incidentIor ) {
		return pow2( ( transmittedIor - incidentIor ) / ( transmittedIor + incidentIor ));
	}
	vec3 evalSensitivity( float OPD, vec3 shift ) {
		float phase = 2.0 * PI * OPD * 1.0e-9;
		vec3 val = vec3( 5.4856e-13, 4.4201e-13, 5.2481e-13 );
		vec3 pos = vec3( 1.6810e+06, 1.7953e+06, 2.2084e+06 );
		vec3 var = vec3( 4.3278e+09, 9.3046e+09, 6.6121e+09 );
		vec3 xyz = val * sqrt( 2.0 * PI * var ) * cos( pos * phase + shift ) * exp( - pow2( phase ) * var );
		xyz.x += 9.7470e-14 * sqrt( 2.0 * PI * 4.5282e+09 ) * cos( 2.2399e+06 * phase + shift[ 0 ] ) * exp( - 4.5282e+09 * pow2( phase ) );
		xyz /= 1.0685e-7;
		vec3 rgb = XYZ_TO_REC709 * xyz;
		return rgb;
	}
	vec3 evalIridescence( float outsideIOR, float eta2, float cosTheta1, float thinFilmThickness, vec3 baseF0 ) {
		vec3 I;
		float iridescenceIOR = mix( outsideIOR, eta2, smoothstep( 0.0, 0.03, thinFilmThickness ) );
		float sinTheta2Sq = pow2( outsideIOR / iridescenceIOR ) * ( 1.0 - pow2( cosTheta1 ) );
		float cosTheta2Sq = 1.0 - sinTheta2Sq;
		if ( cosTheta2Sq < 0.0 ) {
			return vec3( 1.0 );
		}
		float cosTheta2 = sqrt( cosTheta2Sq );
		float R0 = IorToFresnel0( iridescenceIOR, outsideIOR );
		float R12 = F_Schlick( R0, 1.0, cosTheta1 );
		float T121 = 1.0 - R12;
		float phi12 = 0.0;
		if ( iridescenceIOR < outsideIOR ) phi12 = PI;
		float phi21 = PI - phi12;
		vec3 baseIOR = Fresnel0ToIor( clamp( baseF0, 0.0, 0.9999 ) );		vec3 R1 = IorToFresnel0( baseIOR, iridescenceIOR );
		vec3 R23 = F_Schlick( R1, 1.0, cosTheta2 );
		vec3 phi23 = vec3( 0.0 );
		if ( baseIOR[ 0 ] < iridescenceIOR ) phi23[ 0 ] = PI;
		if ( baseIOR[ 1 ] < iridescenceIOR ) phi23[ 1 ] = PI;
		if ( baseIOR[ 2 ] < iridescenceIOR ) phi23[ 2 ] = PI;
		float OPD = 2.0 * iridescenceIOR * thinFilmThickness * cosTheta2;
		vec3 phi = vec3( phi21 ) + phi23;
		vec3 R123 = clamp( R12 * R23, 1e-5, 0.9999 );
		vec3 r123 = sqrt( R123 );
		vec3 Rs = pow2( T121 ) * R23 / ( vec3( 1.0 ) - R123 );
		vec3 C0 = R12 + Rs;
		I = C0;
		vec3 Cm = Rs - T121;
		for ( int m = 1; m <= 2; ++ m ) {
			Cm *= r123;
			vec3 Sm = 2.0 * evalSensitivity( float( m ) * OPD, float( m ) * phi );
			I += Cm * Sm;
		}
		return max( I, vec3( 0.0 ) );
	}
#endif`,$y=`#ifdef USE_BUMPMAP
	uniform sampler2D bumpMap;
	uniform float bumpScale;
	vec2 dHdxy_fwd() {
		vec2 dSTdx = dFdx( vBumpMapUv );
		vec2 dSTdy = dFdy( vBumpMapUv );
		float Hll = bumpScale * texture2D( bumpMap, vBumpMapUv ).x;
		float dBx = bumpScale * texture2D( bumpMap, vBumpMapUv + dSTdx ).x - Hll;
		float dBy = bumpScale * texture2D( bumpMap, vBumpMapUv + dSTdy ).x - Hll;
		return vec2( dBx, dBy );
	}
	vec3 perturbNormalArb( vec3 surf_pos, vec3 surf_norm, vec2 dHdxy, float faceDirection ) {
		vec3 vSigmaX = normalize( dFdx( surf_pos.xyz ) );
		vec3 vSigmaY = normalize( dFdy( surf_pos.xyz ) );
		vec3 vN = surf_norm;
		vec3 R1 = cross( vSigmaY, vN );
		vec3 R2 = cross( vN, vSigmaX );
		float fDet = dot( vSigmaX, R1 ) * faceDirection;
		vec3 vGrad = sign( fDet ) * ( dHdxy.x * R1 + dHdxy.y * R2 );
		return normalize( abs( fDet ) * surf_norm - vGrad );
	}
#endif`,Jy=`#if NUM_CLIPPING_PLANES > 0
	vec4 plane;
	#ifdef ALPHA_TO_COVERAGE
		float distanceToPlane, distanceGradient;
		float clipOpacity = 1.0;
		#pragma unroll_loop_start
		for ( int i = 0; i < UNION_CLIPPING_PLANES; i ++ ) {
			plane = clippingPlanes[ i ];
			distanceToPlane = - dot( vClipPosition, plane.xyz ) + plane.w;
			distanceGradient = fwidth( distanceToPlane ) / 2.0;
			clipOpacity *= smoothstep( - distanceGradient, distanceGradient, distanceToPlane );
			if ( clipOpacity == 0.0 ) discard;
		}
		#pragma unroll_loop_end
		#if UNION_CLIPPING_PLANES < NUM_CLIPPING_PLANES
			float unionClipOpacity = 1.0;
			#pragma unroll_loop_start
			for ( int i = UNION_CLIPPING_PLANES; i < NUM_CLIPPING_PLANES; i ++ ) {
				plane = clippingPlanes[ i ];
				distanceToPlane = - dot( vClipPosition, plane.xyz ) + plane.w;
				distanceGradient = fwidth( distanceToPlane ) / 2.0;
				unionClipOpacity *= 1.0 - smoothstep( - distanceGradient, distanceGradient, distanceToPlane );
			}
			#pragma unroll_loop_end
			clipOpacity *= 1.0 - unionClipOpacity;
		#endif
		diffuseColor.a *= clipOpacity;
		if ( diffuseColor.a == 0.0 ) discard;
	#else
		#pragma unroll_loop_start
		for ( int i = 0; i < UNION_CLIPPING_PLANES; i ++ ) {
			plane = clippingPlanes[ i ];
			if ( dot( vClipPosition, plane.xyz ) > plane.w ) discard;
		}
		#pragma unroll_loop_end
		#if UNION_CLIPPING_PLANES < NUM_CLIPPING_PLANES
			bool clipped = true;
			#pragma unroll_loop_start
			for ( int i = UNION_CLIPPING_PLANES; i < NUM_CLIPPING_PLANES; i ++ ) {
				plane = clippingPlanes[ i ];
				clipped = ( dot( vClipPosition, plane.xyz ) > plane.w ) && clipped;
			}
			#pragma unroll_loop_end
			if ( clipped ) discard;
		#endif
	#endif
#endif`,Ky=`#if NUM_CLIPPING_PLANES > 0
	varying vec3 vClipPosition;
	uniform vec4 clippingPlanes[ NUM_CLIPPING_PLANES ];
#endif`,Qy=`#if NUM_CLIPPING_PLANES > 0
	varying vec3 vClipPosition;
#endif`,jy=`#if NUM_CLIPPING_PLANES > 0
	vClipPosition = - mvPosition.xyz;
#endif`,tM=`#if defined( USE_COLOR_ALPHA )
	diffuseColor *= vColor;
#elif defined( USE_COLOR )
	diffuseColor.rgb *= vColor;
#endif`,eM=`#if defined( USE_COLOR_ALPHA )
	varying vec4 vColor;
#elif defined( USE_COLOR )
	varying vec3 vColor;
#endif`,nM=`#if defined( USE_COLOR_ALPHA )
	varying vec4 vColor;
#elif defined( USE_COLOR ) || defined( USE_INSTANCING_COLOR ) || defined( USE_BATCHING_COLOR )
	varying vec3 vColor;
#endif`,iM=`#if defined( USE_COLOR_ALPHA )
	vColor = vec4( 1.0 );
#elif defined( USE_COLOR ) || defined( USE_INSTANCING_COLOR ) || defined( USE_BATCHING_COLOR )
	vColor = vec3( 1.0 );
#endif
#ifdef USE_COLOR
	vColor *= color;
#endif
#ifdef USE_INSTANCING_COLOR
	vColor.xyz *= instanceColor.xyz;
#endif
#ifdef USE_BATCHING_COLOR
	vec3 batchingColor = getBatchingColor( getIndirectIndex( gl_DrawID ) );
	vColor.xyz *= batchingColor.xyz;
#endif`,sM=`#define PI 3.141592653589793
#define PI2 6.283185307179586
#define PI_HALF 1.5707963267948966
#define RECIPROCAL_PI 0.3183098861837907
#define RECIPROCAL_PI2 0.15915494309189535
#define EPSILON 1e-6
#ifndef saturate
#define saturate( a ) clamp( a, 0.0, 1.0 )
#endif
#define whiteComplement( a ) ( 1.0 - saturate( a ) )
float pow2( const in float x ) { return x*x; }
vec3 pow2( const in vec3 x ) { return x*x; }
float pow3( const in float x ) { return x*x*x; }
float pow4( const in float x ) { float x2 = x*x; return x2*x2; }
float max3( const in vec3 v ) { return max( max( v.x, v.y ), v.z ); }
float average( const in vec3 v ) { return dot( v, vec3( 0.3333333 ) ); }
highp float rand( const in vec2 uv ) {
	const highp float a = 12.9898, b = 78.233, c = 43758.5453;
	highp float dt = dot( uv.xy, vec2( a,b ) ), sn = mod( dt, PI );
	return fract( sin( sn ) * c );
}
#ifdef HIGH_PRECISION
	float precisionSafeLength( vec3 v ) { return length( v ); }
#else
	float precisionSafeLength( vec3 v ) {
		float maxComponent = max3( abs( v ) );
		return length( v / maxComponent ) * maxComponent;
	}
#endif
struct IncidentLight {
	vec3 color;
	vec3 direction;
	bool visible;
};
struct ReflectedLight {
	vec3 directDiffuse;
	vec3 directSpecular;
	vec3 indirectDiffuse;
	vec3 indirectSpecular;
};
#ifdef USE_ALPHAHASH
	varying vec3 vPosition;
#endif
vec3 transformDirection( in vec3 dir, in mat4 matrix ) {
	return normalize( ( matrix * vec4( dir, 0.0 ) ).xyz );
}
vec3 inverseTransformDirection( in vec3 dir, in mat4 matrix ) {
	return normalize( ( vec4( dir, 0.0 ) * matrix ).xyz );
}
mat3 transposeMat3( const in mat3 m ) {
	mat3 tmp;
	tmp[ 0 ] = vec3( m[ 0 ].x, m[ 1 ].x, m[ 2 ].x );
	tmp[ 1 ] = vec3( m[ 0 ].y, m[ 1 ].y, m[ 2 ].y );
	tmp[ 2 ] = vec3( m[ 0 ].z, m[ 1 ].z, m[ 2 ].z );
	return tmp;
}
bool isPerspectiveMatrix( mat4 m ) {
	return m[ 2 ][ 3 ] == - 1.0;
}
vec2 equirectUv( in vec3 dir ) {
	float u = atan( dir.z, dir.x ) * RECIPROCAL_PI2 + 0.5;
	float v = asin( clamp( dir.y, - 1.0, 1.0 ) ) * RECIPROCAL_PI + 0.5;
	return vec2( u, v );
}
vec3 BRDF_Lambert( const in vec3 diffuseColor ) {
	return RECIPROCAL_PI * diffuseColor;
}
vec3 F_Schlick( const in vec3 f0, const in float f90, const in float dotVH ) {
	float fresnel = exp2( ( - 5.55473 * dotVH - 6.98316 ) * dotVH );
	return f0 * ( 1.0 - fresnel ) + ( f90 * fresnel );
}
float F_Schlick( const in float f0, const in float f90, const in float dotVH ) {
	float fresnel = exp2( ( - 5.55473 * dotVH - 6.98316 ) * dotVH );
	return f0 * ( 1.0 - fresnel ) + ( f90 * fresnel );
} // validated`,rM=`#ifdef ENVMAP_TYPE_CUBE_UV
	#define cubeUV_minMipLevel 4.0
	#define cubeUV_minTileSize 16.0
	float getFace( vec3 direction ) {
		vec3 absDirection = abs( direction );
		float face = - 1.0;
		if ( absDirection.x > absDirection.z ) {
			if ( absDirection.x > absDirection.y )
				face = direction.x > 0.0 ? 0.0 : 3.0;
			else
				face = direction.y > 0.0 ? 1.0 : 4.0;
		} else {
			if ( absDirection.z > absDirection.y )
				face = direction.z > 0.0 ? 2.0 : 5.0;
			else
				face = direction.y > 0.0 ? 1.0 : 4.0;
		}
		return face;
	}
	vec2 getUV( vec3 direction, float face ) {
		vec2 uv;
		if ( face == 0.0 ) {
			uv = vec2( direction.z, direction.y ) / abs( direction.x );
		} else if ( face == 1.0 ) {
			uv = vec2( - direction.x, - direction.z ) / abs( direction.y );
		} else if ( face == 2.0 ) {
			uv = vec2( - direction.x, direction.y ) / abs( direction.z );
		} else if ( face == 3.0 ) {
			uv = vec2( - direction.z, direction.y ) / abs( direction.x );
		} else if ( face == 4.0 ) {
			uv = vec2( - direction.x, direction.z ) / abs( direction.y );
		} else {
			uv = vec2( direction.x, direction.y ) / abs( direction.z );
		}
		return 0.5 * ( uv + 1.0 );
	}
	vec3 bilinearCubeUV( sampler2D envMap, vec3 direction, float mipInt ) {
		float face = getFace( direction );
		float filterInt = max( cubeUV_minMipLevel - mipInt, 0.0 );
		mipInt = max( mipInt, cubeUV_minMipLevel );
		float faceSize = exp2( mipInt );
		highp vec2 uv = getUV( direction, face ) * ( faceSize - 2.0 ) + 1.0;
		if ( face > 2.0 ) {
			uv.y += faceSize;
			face -= 3.0;
		}
		uv.x += face * faceSize;
		uv.x += filterInt * 3.0 * cubeUV_minTileSize;
		uv.y += 4.0 * ( exp2( CUBEUV_MAX_MIP ) - faceSize );
		uv.x *= CUBEUV_TEXEL_WIDTH;
		uv.y *= CUBEUV_TEXEL_HEIGHT;
		#ifdef texture2DGradEXT
			return texture2DGradEXT( envMap, uv, vec2( 0.0 ), vec2( 0.0 ) ).rgb;
		#else
			return texture2D( envMap, uv ).rgb;
		#endif
	}
	#define cubeUV_r0 1.0
	#define cubeUV_m0 - 2.0
	#define cubeUV_r1 0.8
	#define cubeUV_m1 - 1.0
	#define cubeUV_r4 0.4
	#define cubeUV_m4 2.0
	#define cubeUV_r5 0.305
	#define cubeUV_m5 3.0
	#define cubeUV_r6 0.21
	#define cubeUV_m6 4.0
	float roughnessToMip( float roughness ) {
		float mip = 0.0;
		if ( roughness >= cubeUV_r1 ) {
			mip = ( cubeUV_r0 - roughness ) * ( cubeUV_m1 - cubeUV_m0 ) / ( cubeUV_r0 - cubeUV_r1 ) + cubeUV_m0;
		} else if ( roughness >= cubeUV_r4 ) {
			mip = ( cubeUV_r1 - roughness ) * ( cubeUV_m4 - cubeUV_m1 ) / ( cubeUV_r1 - cubeUV_r4 ) + cubeUV_m1;
		} else if ( roughness >= cubeUV_r5 ) {
			mip = ( cubeUV_r4 - roughness ) * ( cubeUV_m5 - cubeUV_m4 ) / ( cubeUV_r4 - cubeUV_r5 ) + cubeUV_m4;
		} else if ( roughness >= cubeUV_r6 ) {
			mip = ( cubeUV_r5 - roughness ) * ( cubeUV_m6 - cubeUV_m5 ) / ( cubeUV_r5 - cubeUV_r6 ) + cubeUV_m5;
		} else {
			mip = - 2.0 * log2( 1.16 * roughness );		}
		return mip;
	}
	vec4 textureCubeUV( sampler2D envMap, vec3 sampleDir, float roughness ) {
		float mip = clamp( roughnessToMip( roughness ), cubeUV_m0, CUBEUV_MAX_MIP );
		float mipF = fract( mip );
		float mipInt = floor( mip );
		vec3 color0 = bilinearCubeUV( envMap, sampleDir, mipInt );
		if ( mipF == 0.0 ) {
			return vec4( color0, 1.0 );
		} else {
			vec3 color1 = bilinearCubeUV( envMap, sampleDir, mipInt + 1.0 );
			return vec4( mix( color0, color1, mipF ), 1.0 );
		}
	}
#endif`,oM=`vec3 transformedNormal = objectNormal;
#ifdef USE_TANGENT
	vec3 transformedTangent = objectTangent;
#endif
#ifdef USE_BATCHING
	mat3 bm = mat3( batchingMatrix );
	transformedNormal /= vec3( dot( bm[ 0 ], bm[ 0 ] ), dot( bm[ 1 ], bm[ 1 ] ), dot( bm[ 2 ], bm[ 2 ] ) );
	transformedNormal = bm * transformedNormal;
	#ifdef USE_TANGENT
		transformedTangent = bm * transformedTangent;
	#endif
#endif
#ifdef USE_INSTANCING
	mat3 im = mat3( instanceMatrix );
	transformedNormal /= vec3( dot( im[ 0 ], im[ 0 ] ), dot( im[ 1 ], im[ 1 ] ), dot( im[ 2 ], im[ 2 ] ) );
	transformedNormal = im * transformedNormal;
	#ifdef USE_TANGENT
		transformedTangent = im * transformedTangent;
	#endif
#endif
transformedNormal = normalMatrix * transformedNormal;
#ifdef FLIP_SIDED
	transformedNormal = - transformedNormal;
#endif
#ifdef USE_TANGENT
	transformedTangent = ( modelViewMatrix * vec4( transformedTangent, 0.0 ) ).xyz;
	#ifdef FLIP_SIDED
		transformedTangent = - transformedTangent;
	#endif
#endif`,aM=`#ifdef USE_DISPLACEMENTMAP
	uniform sampler2D displacementMap;
	uniform float displacementScale;
	uniform float displacementBias;
#endif`,lM=`#ifdef USE_DISPLACEMENTMAP
	transformed += normalize( objectNormal ) * ( texture2D( displacementMap, vDisplacementMapUv ).x * displacementScale + displacementBias );
#endif`,cM=`#ifdef USE_EMISSIVEMAP
	vec4 emissiveColor = texture2D( emissiveMap, vEmissiveMapUv );
	#ifdef DECODE_VIDEO_TEXTURE_EMISSIVE
		emissiveColor = sRGBTransferEOTF( emissiveColor );
	#endif
	totalEmissiveRadiance *= emissiveColor.rgb;
#endif`,hM=`#ifdef USE_EMISSIVEMAP
	uniform sampler2D emissiveMap;
#endif`,uM="gl_FragColor = linearToOutputTexel( gl_FragColor );",fM=`vec4 LinearTransferOETF( in vec4 value ) {
	return value;
}
vec4 sRGBTransferEOTF( in vec4 value ) {
	return vec4( mix( pow( value.rgb * 0.9478672986 + vec3( 0.0521327014 ), vec3( 2.4 ) ), value.rgb * 0.0773993808, vec3( lessThanEqual( value.rgb, vec3( 0.04045 ) ) ) ), value.a );
}
vec4 sRGBTransferOETF( in vec4 value ) {
	return vec4( mix( pow( value.rgb, vec3( 0.41666 ) ) * 1.055 - vec3( 0.055 ), value.rgb * 12.92, vec3( lessThanEqual( value.rgb, vec3( 0.0031308 ) ) ) ), value.a );
}`,dM=`#ifdef USE_ENVMAP
	#ifdef ENV_WORLDPOS
		vec3 cameraToFrag;
		if ( isOrthographic ) {
			cameraToFrag = normalize( vec3( - viewMatrix[ 0 ][ 2 ], - viewMatrix[ 1 ][ 2 ], - viewMatrix[ 2 ][ 2 ] ) );
		} else {
			cameraToFrag = normalize( vWorldPosition - cameraPosition );
		}
		vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
		#ifdef ENVMAP_MODE_REFLECTION
			vec3 reflectVec = reflect( cameraToFrag, worldNormal );
		#else
			vec3 reflectVec = refract( cameraToFrag, worldNormal, refractionRatio );
		#endif
	#else
		vec3 reflectVec = vReflect;
	#endif
	#ifdef ENVMAP_TYPE_CUBE
		vec4 envColor = textureCube( envMap, envMapRotation * vec3( flipEnvMap * reflectVec.x, reflectVec.yz ) );
	#else
		vec4 envColor = vec4( 0.0 );
	#endif
	#ifdef ENVMAP_BLENDING_MULTIPLY
		outgoingLight = mix( outgoingLight, outgoingLight * envColor.xyz, specularStrength * reflectivity );
	#elif defined( ENVMAP_BLENDING_MIX )
		outgoingLight = mix( outgoingLight, envColor.xyz, specularStrength * reflectivity );
	#elif defined( ENVMAP_BLENDING_ADD )
		outgoingLight += envColor.xyz * specularStrength * reflectivity;
	#endif
#endif`,pM=`#ifdef USE_ENVMAP
	uniform float envMapIntensity;
	uniform float flipEnvMap;
	uniform mat3 envMapRotation;
	#ifdef ENVMAP_TYPE_CUBE
		uniform samplerCube envMap;
	#else
		uniform sampler2D envMap;
	#endif
	
#endif`,mM=`#ifdef USE_ENVMAP
	uniform float reflectivity;
	#if defined( USE_BUMPMAP ) || defined( USE_NORMALMAP ) || defined( PHONG ) || defined( LAMBERT )
		#define ENV_WORLDPOS
	#endif
	#ifdef ENV_WORLDPOS
		varying vec3 vWorldPosition;
		uniform float refractionRatio;
	#else
		varying vec3 vReflect;
	#endif
#endif`,gM=`#ifdef USE_ENVMAP
	#if defined( USE_BUMPMAP ) || defined( USE_NORMALMAP ) || defined( PHONG ) || defined( LAMBERT )
		#define ENV_WORLDPOS
	#endif
	#ifdef ENV_WORLDPOS
		
		varying vec3 vWorldPosition;
	#else
		varying vec3 vReflect;
		uniform float refractionRatio;
	#endif
#endif`,_M=`#ifdef USE_ENVMAP
	#ifdef ENV_WORLDPOS
		vWorldPosition = worldPosition.xyz;
	#else
		vec3 cameraToVertex;
		if ( isOrthographic ) {
			cameraToVertex = normalize( vec3( - viewMatrix[ 0 ][ 2 ], - viewMatrix[ 1 ][ 2 ], - viewMatrix[ 2 ][ 2 ] ) );
		} else {
			cameraToVertex = normalize( worldPosition.xyz - cameraPosition );
		}
		vec3 worldNormal = inverseTransformDirection( transformedNormal, viewMatrix );
		#ifdef ENVMAP_MODE_REFLECTION
			vReflect = reflect( cameraToVertex, worldNormal );
		#else
			vReflect = refract( cameraToVertex, worldNormal, refractionRatio );
		#endif
	#endif
#endif`,vM=`#ifdef USE_FOG
	vFogDepth = - mvPosition.z;
#endif`,xM=`#ifdef USE_FOG
	varying float vFogDepth;
#endif`,yM=`#ifdef USE_FOG
	#ifdef FOG_EXP2
		float fogFactor = 1.0 - exp( - fogDensity * fogDensity * vFogDepth * vFogDepth );
	#else
		float fogFactor = smoothstep( fogNear, fogFar, vFogDepth );
	#endif
	gl_FragColor.rgb = mix( gl_FragColor.rgb, fogColor, fogFactor );
#endif`,MM=`#ifdef USE_FOG
	uniform vec3 fogColor;
	varying float vFogDepth;
	#ifdef FOG_EXP2
		uniform float fogDensity;
	#else
		uniform float fogNear;
		uniform float fogFar;
	#endif
#endif`,SM=`#ifdef USE_GRADIENTMAP
	uniform sampler2D gradientMap;
#endif
vec3 getGradientIrradiance( vec3 normal, vec3 lightDirection ) {
	float dotNL = dot( normal, lightDirection );
	vec2 coord = vec2( dotNL * 0.5 + 0.5, 0.0 );
	#ifdef USE_GRADIENTMAP
		return vec3( texture2D( gradientMap, coord ).r );
	#else
		vec2 fw = fwidth( coord ) * 0.5;
		return mix( vec3( 0.7 ), vec3( 1.0 ), smoothstep( 0.7 - fw.x, 0.7 + fw.x, coord.x ) );
	#endif
}`,bM=`#ifdef USE_LIGHTMAP
	uniform sampler2D lightMap;
	uniform float lightMapIntensity;
#endif`,wM=`LambertMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.specularStrength = specularStrength;`,TM=`varying vec3 vViewPosition;
struct LambertMaterial {
	vec3 diffuseColor;
	float specularStrength;
};
void RE_Direct_Lambert( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in LambertMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Lambert( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in LambertMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_Lambert
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Lambert`,EM=`uniform bool receiveShadow;
uniform vec3 ambientLightColor;
#if defined( USE_LIGHT_PROBES )
	uniform vec3 lightProbe[ 9 ];
#endif
vec3 shGetIrradianceAt( in vec3 normal, in vec3 shCoefficients[ 9 ] ) {
	float x = normal.x, y = normal.y, z = normal.z;
	vec3 result = shCoefficients[ 0 ] * 0.886227;
	result += shCoefficients[ 1 ] * 2.0 * 0.511664 * y;
	result += shCoefficients[ 2 ] * 2.0 * 0.511664 * z;
	result += shCoefficients[ 3 ] * 2.0 * 0.511664 * x;
	result += shCoefficients[ 4 ] * 2.0 * 0.429043 * x * y;
	result += shCoefficients[ 5 ] * 2.0 * 0.429043 * y * z;
	result += shCoefficients[ 6 ] * ( 0.743125 * z * z - 0.247708 );
	result += shCoefficients[ 7 ] * 2.0 * 0.429043 * x * z;
	result += shCoefficients[ 8 ] * 0.429043 * ( x * x - y * y );
	return result;
}
vec3 getLightProbeIrradiance( const in vec3 lightProbe[ 9 ], const in vec3 normal ) {
	vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
	vec3 irradiance = shGetIrradianceAt( worldNormal, lightProbe );
	return irradiance;
}
vec3 getAmbientLightIrradiance( const in vec3 ambientLightColor ) {
	vec3 irradiance = ambientLightColor;
	return irradiance;
}
float getDistanceAttenuation( const in float lightDistance, const in float cutoffDistance, const in float decayExponent ) {
	float distanceFalloff = 1.0 / max( pow( lightDistance, decayExponent ), 0.01 );
	if ( cutoffDistance > 0.0 ) {
		distanceFalloff *= pow2( saturate( 1.0 - pow4( lightDistance / cutoffDistance ) ) );
	}
	return distanceFalloff;
}
float getSpotAttenuation( const in float coneCosine, const in float penumbraCosine, const in float angleCosine ) {
	return smoothstep( coneCosine, penumbraCosine, angleCosine );
}
#if NUM_DIR_LIGHTS > 0
	struct DirectionalLight {
		vec3 direction;
		vec3 color;
	};
	uniform DirectionalLight directionalLights[ NUM_DIR_LIGHTS ];
	void getDirectionalLightInfo( const in DirectionalLight directionalLight, out IncidentLight light ) {
		light.color = directionalLight.color;
		light.direction = directionalLight.direction;
		light.visible = true;
	}
#endif
#if NUM_POINT_LIGHTS > 0
	struct PointLight {
		vec3 position;
		vec3 color;
		float distance;
		float decay;
	};
	uniform PointLight pointLights[ NUM_POINT_LIGHTS ];
	void getPointLightInfo( const in PointLight pointLight, const in vec3 geometryPosition, out IncidentLight light ) {
		vec3 lVector = pointLight.position - geometryPosition;
		light.direction = normalize( lVector );
		float lightDistance = length( lVector );
		light.color = pointLight.color;
		light.color *= getDistanceAttenuation( lightDistance, pointLight.distance, pointLight.decay );
		light.visible = ( light.color != vec3( 0.0 ) );
	}
#endif
#if NUM_SPOT_LIGHTS > 0
	struct SpotLight {
		vec3 position;
		vec3 direction;
		vec3 color;
		float distance;
		float decay;
		float coneCos;
		float penumbraCos;
	};
	uniform SpotLight spotLights[ NUM_SPOT_LIGHTS ];
	void getSpotLightInfo( const in SpotLight spotLight, const in vec3 geometryPosition, out IncidentLight light ) {
		vec3 lVector = spotLight.position - geometryPosition;
		light.direction = normalize( lVector );
		float angleCos = dot( light.direction, spotLight.direction );
		float spotAttenuation = getSpotAttenuation( spotLight.coneCos, spotLight.penumbraCos, angleCos );
		if ( spotAttenuation > 0.0 ) {
			float lightDistance = length( lVector );
			light.color = spotLight.color * spotAttenuation;
			light.color *= getDistanceAttenuation( lightDistance, spotLight.distance, spotLight.decay );
			light.visible = ( light.color != vec3( 0.0 ) );
		} else {
			light.color = vec3( 0.0 );
			light.visible = false;
		}
	}
#endif
#if NUM_RECT_AREA_LIGHTS > 0
	struct RectAreaLight {
		vec3 color;
		vec3 position;
		vec3 halfWidth;
		vec3 halfHeight;
	};
	uniform sampler2D ltc_1;	uniform sampler2D ltc_2;
	uniform RectAreaLight rectAreaLights[ NUM_RECT_AREA_LIGHTS ];
#endif
#if NUM_HEMI_LIGHTS > 0
	struct HemisphereLight {
		vec3 direction;
		vec3 skyColor;
		vec3 groundColor;
	};
	uniform HemisphereLight hemisphereLights[ NUM_HEMI_LIGHTS ];
	vec3 getHemisphereLightIrradiance( const in HemisphereLight hemiLight, const in vec3 normal ) {
		float dotNL = dot( normal, hemiLight.direction );
		float hemiDiffuseWeight = 0.5 * dotNL + 0.5;
		vec3 irradiance = mix( hemiLight.groundColor, hemiLight.skyColor, hemiDiffuseWeight );
		return irradiance;
	}
#endif`,AM=`#ifdef USE_ENVMAP
	vec3 getIBLIrradiance( const in vec3 normal ) {
		#ifdef ENVMAP_TYPE_CUBE_UV
			vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
			vec4 envMapColor = textureCubeUV( envMap, envMapRotation * worldNormal, 1.0 );
			return PI * envMapColor.rgb * envMapIntensity;
		#else
			return vec3( 0.0 );
		#endif
	}
	vec3 getIBLRadiance( const in vec3 viewDir, const in vec3 normal, const in float roughness ) {
		#ifdef ENVMAP_TYPE_CUBE_UV
			vec3 reflectVec = reflect( - viewDir, normal );
			reflectVec = normalize( mix( reflectVec, normal, roughness * roughness) );
			reflectVec = inverseTransformDirection( reflectVec, viewMatrix );
			vec4 envMapColor = textureCubeUV( envMap, envMapRotation * reflectVec, roughness );
			return envMapColor.rgb * envMapIntensity;
		#else
			return vec3( 0.0 );
		#endif
	}
	#ifdef USE_ANISOTROPY
		vec3 getIBLAnisotropyRadiance( const in vec3 viewDir, const in vec3 normal, const in float roughness, const in vec3 bitangent, const in float anisotropy ) {
			#ifdef ENVMAP_TYPE_CUBE_UV
				vec3 bentNormal = cross( bitangent, viewDir );
				bentNormal = normalize( cross( bentNormal, bitangent ) );
				bentNormal = normalize( mix( bentNormal, normal, pow2( pow2( 1.0 - anisotropy * ( 1.0 - roughness ) ) ) ) );
				return getIBLRadiance( viewDir, bentNormal, roughness );
			#else
				return vec3( 0.0 );
			#endif
		}
	#endif
#endif`,CM=`ToonMaterial material;
material.diffuseColor = diffuseColor.rgb;`,RM=`varying vec3 vViewPosition;
struct ToonMaterial {
	vec3 diffuseColor;
};
void RE_Direct_Toon( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in ToonMaterial material, inout ReflectedLight reflectedLight ) {
	vec3 irradiance = getGradientIrradiance( geometryNormal, directLight.direction ) * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Toon( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in ToonMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_Toon
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Toon`,PM=`BlinnPhongMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.specularColor = specular;
material.specularShininess = shininess;
material.specularStrength = specularStrength;`,IM=`varying vec3 vViewPosition;
struct BlinnPhongMaterial {
	vec3 diffuseColor;
	vec3 specularColor;
	float specularShininess;
	float specularStrength;
};
void RE_Direct_BlinnPhong( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in BlinnPhongMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
	reflectedLight.directSpecular += irradiance * BRDF_BlinnPhong( directLight.direction, geometryViewDir, geometryNormal, material.specularColor, material.specularShininess ) * material.specularStrength;
}
void RE_IndirectDiffuse_BlinnPhong( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in BlinnPhongMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_BlinnPhong
#define RE_IndirectDiffuse		RE_IndirectDiffuse_BlinnPhong`,LM=`PhysicalMaterial material;
material.diffuseColor = diffuseColor.rgb * ( 1.0 - metalnessFactor );
vec3 dxy = max( abs( dFdx( nonPerturbedNormal ) ), abs( dFdy( nonPerturbedNormal ) ) );
float geometryRoughness = max( max( dxy.x, dxy.y ), dxy.z );
material.roughness = max( roughnessFactor, 0.0525 );material.roughness += geometryRoughness;
material.roughness = min( material.roughness, 1.0 );
#ifdef IOR
	material.ior = ior;
	#ifdef USE_SPECULAR
		float specularIntensityFactor = specularIntensity;
		vec3 specularColorFactor = specularColor;
		#ifdef USE_SPECULAR_COLORMAP
			specularColorFactor *= texture2D( specularColorMap, vSpecularColorMapUv ).rgb;
		#endif
		#ifdef USE_SPECULAR_INTENSITYMAP
			specularIntensityFactor *= texture2D( specularIntensityMap, vSpecularIntensityMapUv ).a;
		#endif
		material.specularF90 = mix( specularIntensityFactor, 1.0, metalnessFactor );
	#else
		float specularIntensityFactor = 1.0;
		vec3 specularColorFactor = vec3( 1.0 );
		material.specularF90 = 1.0;
	#endif
	material.specularColor = mix( min( pow2( ( material.ior - 1.0 ) / ( material.ior + 1.0 ) ) * specularColorFactor, vec3( 1.0 ) ) * specularIntensityFactor, diffuseColor.rgb, metalnessFactor );
#else
	material.specularColor = mix( vec3( 0.04 ), diffuseColor.rgb, metalnessFactor );
	material.specularF90 = 1.0;
#endif
#ifdef USE_CLEARCOAT
	material.clearcoat = clearcoat;
	material.clearcoatRoughness = clearcoatRoughness;
	material.clearcoatF0 = vec3( 0.04 );
	material.clearcoatF90 = 1.0;
	#ifdef USE_CLEARCOATMAP
		material.clearcoat *= texture2D( clearcoatMap, vClearcoatMapUv ).x;
	#endif
	#ifdef USE_CLEARCOAT_ROUGHNESSMAP
		material.clearcoatRoughness *= texture2D( clearcoatRoughnessMap, vClearcoatRoughnessMapUv ).y;
	#endif
	material.clearcoat = saturate( material.clearcoat );	material.clearcoatRoughness = max( material.clearcoatRoughness, 0.0525 );
	material.clearcoatRoughness += geometryRoughness;
	material.clearcoatRoughness = min( material.clearcoatRoughness, 1.0 );
#endif
#ifdef USE_DISPERSION
	material.dispersion = dispersion;
#endif
#ifdef USE_IRIDESCENCE
	material.iridescence = iridescence;
	material.iridescenceIOR = iridescenceIOR;
	#ifdef USE_IRIDESCENCEMAP
		material.iridescence *= texture2D( iridescenceMap, vIridescenceMapUv ).r;
	#endif
	#ifdef USE_IRIDESCENCE_THICKNESSMAP
		material.iridescenceThickness = (iridescenceThicknessMaximum - iridescenceThicknessMinimum) * texture2D( iridescenceThicknessMap, vIridescenceThicknessMapUv ).g + iridescenceThicknessMinimum;
	#else
		material.iridescenceThickness = iridescenceThicknessMaximum;
	#endif
#endif
#ifdef USE_SHEEN
	material.sheenColor = sheenColor;
	#ifdef USE_SHEEN_COLORMAP
		material.sheenColor *= texture2D( sheenColorMap, vSheenColorMapUv ).rgb;
	#endif
	material.sheenRoughness = clamp( sheenRoughness, 0.07, 1.0 );
	#ifdef USE_SHEEN_ROUGHNESSMAP
		material.sheenRoughness *= texture2D( sheenRoughnessMap, vSheenRoughnessMapUv ).a;
	#endif
#endif
#ifdef USE_ANISOTROPY
	#ifdef USE_ANISOTROPYMAP
		mat2 anisotropyMat = mat2( anisotropyVector.x, anisotropyVector.y, - anisotropyVector.y, anisotropyVector.x );
		vec3 anisotropyPolar = texture2D( anisotropyMap, vAnisotropyMapUv ).rgb;
		vec2 anisotropyV = anisotropyMat * normalize( 2.0 * anisotropyPolar.rg - vec2( 1.0 ) ) * anisotropyPolar.b;
	#else
		vec2 anisotropyV = anisotropyVector;
	#endif
	material.anisotropy = length( anisotropyV );
	if( material.anisotropy == 0.0 ) {
		anisotropyV = vec2( 1.0, 0.0 );
	} else {
		anisotropyV /= material.anisotropy;
		material.anisotropy = saturate( material.anisotropy );
	}
	material.alphaT = mix( pow2( material.roughness ), 1.0, pow2( material.anisotropy ) );
	material.anisotropyT = tbn[ 0 ] * anisotropyV.x + tbn[ 1 ] * anisotropyV.y;
	material.anisotropyB = tbn[ 1 ] * anisotropyV.x - tbn[ 0 ] * anisotropyV.y;
#endif`,DM=`struct PhysicalMaterial {
	vec3 diffuseColor;
	float roughness;
	vec3 specularColor;
	float specularF90;
	float dispersion;
	#ifdef USE_CLEARCOAT
		float clearcoat;
		float clearcoatRoughness;
		vec3 clearcoatF0;
		float clearcoatF90;
	#endif
	#ifdef USE_IRIDESCENCE
		float iridescence;
		float iridescenceIOR;
		float iridescenceThickness;
		vec3 iridescenceFresnel;
		vec3 iridescenceF0;
	#endif
	#ifdef USE_SHEEN
		vec3 sheenColor;
		float sheenRoughness;
	#endif
	#ifdef IOR
		float ior;
	#endif
	#ifdef USE_TRANSMISSION
		float transmission;
		float transmissionAlpha;
		float thickness;
		float attenuationDistance;
		vec3 attenuationColor;
	#endif
	#ifdef USE_ANISOTROPY
		float anisotropy;
		float alphaT;
		vec3 anisotropyT;
		vec3 anisotropyB;
	#endif
};
vec3 clearcoatSpecularDirect = vec3( 0.0 );
vec3 clearcoatSpecularIndirect = vec3( 0.0 );
vec3 sheenSpecularDirect = vec3( 0.0 );
vec3 sheenSpecularIndirect = vec3(0.0 );
vec3 Schlick_to_F0( const in vec3 f, const in float f90, const in float dotVH ) {
    float x = clamp( 1.0 - dotVH, 0.0, 1.0 );
    float x2 = x * x;
    float x5 = clamp( x * x2 * x2, 0.0, 0.9999 );
    return ( f - vec3( f90 ) * x5 ) / ( 1.0 - x5 );
}
float V_GGX_SmithCorrelated( const in float alpha, const in float dotNL, const in float dotNV ) {
	float a2 = pow2( alpha );
	float gv = dotNL * sqrt( a2 + ( 1.0 - a2 ) * pow2( dotNV ) );
	float gl = dotNV * sqrt( a2 + ( 1.0 - a2 ) * pow2( dotNL ) );
	return 0.5 / max( gv + gl, EPSILON );
}
float D_GGX( const in float alpha, const in float dotNH ) {
	float a2 = pow2( alpha );
	float denom = pow2( dotNH ) * ( a2 - 1.0 ) + 1.0;
	return RECIPROCAL_PI * a2 / pow2( denom );
}
#ifdef USE_ANISOTROPY
	float V_GGX_SmithCorrelated_Anisotropic( const in float alphaT, const in float alphaB, const in float dotTV, const in float dotBV, const in float dotTL, const in float dotBL, const in float dotNV, const in float dotNL ) {
		float gv = dotNL * length( vec3( alphaT * dotTV, alphaB * dotBV, dotNV ) );
		float gl = dotNV * length( vec3( alphaT * dotTL, alphaB * dotBL, dotNL ) );
		float v = 0.5 / ( gv + gl );
		return saturate(v);
	}
	float D_GGX_Anisotropic( const in float alphaT, const in float alphaB, const in float dotNH, const in float dotTH, const in float dotBH ) {
		float a2 = alphaT * alphaB;
		highp vec3 v = vec3( alphaB * dotTH, alphaT * dotBH, a2 * dotNH );
		highp float v2 = dot( v, v );
		float w2 = a2 / v2;
		return RECIPROCAL_PI * a2 * pow2 ( w2 );
	}
#endif
#ifdef USE_CLEARCOAT
	vec3 BRDF_GGX_Clearcoat( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in PhysicalMaterial material) {
		vec3 f0 = material.clearcoatF0;
		float f90 = material.clearcoatF90;
		float roughness = material.clearcoatRoughness;
		float alpha = pow2( roughness );
		vec3 halfDir = normalize( lightDir + viewDir );
		float dotNL = saturate( dot( normal, lightDir ) );
		float dotNV = saturate( dot( normal, viewDir ) );
		float dotNH = saturate( dot( normal, halfDir ) );
		float dotVH = saturate( dot( viewDir, halfDir ) );
		vec3 F = F_Schlick( f0, f90, dotVH );
		float V = V_GGX_SmithCorrelated( alpha, dotNL, dotNV );
		float D = D_GGX( alpha, dotNH );
		return F * ( V * D );
	}
#endif
vec3 BRDF_GGX( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in PhysicalMaterial material ) {
	vec3 f0 = material.specularColor;
	float f90 = material.specularF90;
	float roughness = material.roughness;
	float alpha = pow2( roughness );
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNL = saturate( dot( normal, lightDir ) );
	float dotNV = saturate( dot( normal, viewDir ) );
	float dotNH = saturate( dot( normal, halfDir ) );
	float dotVH = saturate( dot( viewDir, halfDir ) );
	vec3 F = F_Schlick( f0, f90, dotVH );
	#ifdef USE_IRIDESCENCE
		F = mix( F, material.iridescenceFresnel, material.iridescence );
	#endif
	#ifdef USE_ANISOTROPY
		float dotTL = dot( material.anisotropyT, lightDir );
		float dotTV = dot( material.anisotropyT, viewDir );
		float dotTH = dot( material.anisotropyT, halfDir );
		float dotBL = dot( material.anisotropyB, lightDir );
		float dotBV = dot( material.anisotropyB, viewDir );
		float dotBH = dot( material.anisotropyB, halfDir );
		float V = V_GGX_SmithCorrelated_Anisotropic( material.alphaT, alpha, dotTV, dotBV, dotTL, dotBL, dotNV, dotNL );
		float D = D_GGX_Anisotropic( material.alphaT, alpha, dotNH, dotTH, dotBH );
	#else
		float V = V_GGX_SmithCorrelated( alpha, dotNL, dotNV );
		float D = D_GGX( alpha, dotNH );
	#endif
	return F * ( V * D );
}
vec2 LTC_Uv( const in vec3 N, const in vec3 V, const in float roughness ) {
	const float LUT_SIZE = 64.0;
	const float LUT_SCALE = ( LUT_SIZE - 1.0 ) / LUT_SIZE;
	const float LUT_BIAS = 0.5 / LUT_SIZE;
	float dotNV = saturate( dot( N, V ) );
	vec2 uv = vec2( roughness, sqrt( 1.0 - dotNV ) );
	uv = uv * LUT_SCALE + LUT_BIAS;
	return uv;
}
float LTC_ClippedSphereFormFactor( const in vec3 f ) {
	float l = length( f );
	return max( ( l * l + f.z ) / ( l + 1.0 ), 0.0 );
}
vec3 LTC_EdgeVectorFormFactor( const in vec3 v1, const in vec3 v2 ) {
	float x = dot( v1, v2 );
	float y = abs( x );
	float a = 0.8543985 + ( 0.4965155 + 0.0145206 * y ) * y;
	float b = 3.4175940 + ( 4.1616724 + y ) * y;
	float v = a / b;
	float theta_sintheta = ( x > 0.0 ) ? v : 0.5 * inversesqrt( max( 1.0 - x * x, 1e-7 ) ) - v;
	return cross( v1, v2 ) * theta_sintheta;
}
vec3 LTC_Evaluate( const in vec3 N, const in vec3 V, const in vec3 P, const in mat3 mInv, const in vec3 rectCoords[ 4 ] ) {
	vec3 v1 = rectCoords[ 1 ] - rectCoords[ 0 ];
	vec3 v2 = rectCoords[ 3 ] - rectCoords[ 0 ];
	vec3 lightNormal = cross( v1, v2 );
	if( dot( lightNormal, P - rectCoords[ 0 ] ) < 0.0 ) return vec3( 0.0 );
	vec3 T1, T2;
	T1 = normalize( V - N * dot( V, N ) );
	T2 = - cross( N, T1 );
	mat3 mat = mInv * transposeMat3( mat3( T1, T2, N ) );
	vec3 coords[ 4 ];
	coords[ 0 ] = mat * ( rectCoords[ 0 ] - P );
	coords[ 1 ] = mat * ( rectCoords[ 1 ] - P );
	coords[ 2 ] = mat * ( rectCoords[ 2 ] - P );
	coords[ 3 ] = mat * ( rectCoords[ 3 ] - P );
	coords[ 0 ] = normalize( coords[ 0 ] );
	coords[ 1 ] = normalize( coords[ 1 ] );
	coords[ 2 ] = normalize( coords[ 2 ] );
	coords[ 3 ] = normalize( coords[ 3 ] );
	vec3 vectorFormFactor = vec3( 0.0 );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 0 ], coords[ 1 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 1 ], coords[ 2 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 2 ], coords[ 3 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 3 ], coords[ 0 ] );
	float result = LTC_ClippedSphereFormFactor( vectorFormFactor );
	return vec3( result );
}
#if defined( USE_SHEEN )
float D_Charlie( float roughness, float dotNH ) {
	float alpha = pow2( roughness );
	float invAlpha = 1.0 / alpha;
	float cos2h = dotNH * dotNH;
	float sin2h = max( 1.0 - cos2h, 0.0078125 );
	return ( 2.0 + invAlpha ) * pow( sin2h, invAlpha * 0.5 ) / ( 2.0 * PI );
}
float V_Neubelt( float dotNV, float dotNL ) {
	return saturate( 1.0 / ( 4.0 * ( dotNL + dotNV - dotNL * dotNV ) ) );
}
vec3 BRDF_Sheen( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, vec3 sheenColor, const in float sheenRoughness ) {
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNL = saturate( dot( normal, lightDir ) );
	float dotNV = saturate( dot( normal, viewDir ) );
	float dotNH = saturate( dot( normal, halfDir ) );
	float D = D_Charlie( sheenRoughness, dotNH );
	float V = V_Neubelt( dotNV, dotNL );
	return sheenColor * ( D * V );
}
#endif
float IBLSheenBRDF( const in vec3 normal, const in vec3 viewDir, const in float roughness ) {
	float dotNV = saturate( dot( normal, viewDir ) );
	float r2 = roughness * roughness;
	float a = roughness < 0.25 ? -339.2 * r2 + 161.4 * roughness - 25.9 : -8.48 * r2 + 14.3 * roughness - 9.95;
	float b = roughness < 0.25 ? 44.0 * r2 - 23.7 * roughness + 3.26 : 1.97 * r2 - 3.27 * roughness + 0.72;
	float DG = exp( a * dotNV + b ) + ( roughness < 0.25 ? 0.0 : 0.1 * ( roughness - 0.25 ) );
	return saturate( DG * RECIPROCAL_PI );
}
vec2 DFGApprox( const in vec3 normal, const in vec3 viewDir, const in float roughness ) {
	float dotNV = saturate( dot( normal, viewDir ) );
	const vec4 c0 = vec4( - 1, - 0.0275, - 0.572, 0.022 );
	const vec4 c1 = vec4( 1, 0.0425, 1.04, - 0.04 );
	vec4 r = roughness * c0 + c1;
	float a004 = min( r.x * r.x, exp2( - 9.28 * dotNV ) ) * r.x + r.y;
	vec2 fab = vec2( - 1.04, 1.04 ) * a004 + r.zw;
	return fab;
}
vec3 EnvironmentBRDF( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float roughness ) {
	vec2 fab = DFGApprox( normal, viewDir, roughness );
	return specularColor * fab.x + specularF90 * fab.y;
}
#ifdef USE_IRIDESCENCE
void computeMultiscatteringIridescence( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float iridescence, const in vec3 iridescenceF0, const in float roughness, inout vec3 singleScatter, inout vec3 multiScatter ) {
#else
void computeMultiscattering( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float roughness, inout vec3 singleScatter, inout vec3 multiScatter ) {
#endif
	vec2 fab = DFGApprox( normal, viewDir, roughness );
	#ifdef USE_IRIDESCENCE
		vec3 Fr = mix( specularColor, iridescenceF0, iridescence );
	#else
		vec3 Fr = specularColor;
	#endif
	vec3 FssEss = Fr * fab.x + specularF90 * fab.y;
	float Ess = fab.x + fab.y;
	float Ems = 1.0 - Ess;
	vec3 Favg = Fr + ( 1.0 - Fr ) * 0.047619;	vec3 Fms = FssEss * Favg / ( 1.0 - Ems * Favg );
	singleScatter += FssEss;
	multiScatter += Fms * Ems;
}
#if NUM_RECT_AREA_LIGHTS > 0
	void RE_Direct_RectArea_Physical( const in RectAreaLight rectAreaLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
		vec3 normal = geometryNormal;
		vec3 viewDir = geometryViewDir;
		vec3 position = geometryPosition;
		vec3 lightPos = rectAreaLight.position;
		vec3 halfWidth = rectAreaLight.halfWidth;
		vec3 halfHeight = rectAreaLight.halfHeight;
		vec3 lightColor = rectAreaLight.color;
		float roughness = material.roughness;
		vec3 rectCoords[ 4 ];
		rectCoords[ 0 ] = lightPos + halfWidth - halfHeight;		rectCoords[ 1 ] = lightPos - halfWidth - halfHeight;
		rectCoords[ 2 ] = lightPos - halfWidth + halfHeight;
		rectCoords[ 3 ] = lightPos + halfWidth + halfHeight;
		vec2 uv = LTC_Uv( normal, viewDir, roughness );
		vec4 t1 = texture2D( ltc_1, uv );
		vec4 t2 = texture2D( ltc_2, uv );
		mat3 mInv = mat3(
			vec3( t1.x, 0, t1.y ),
			vec3(    0, 1,    0 ),
			vec3( t1.z, 0, t1.w )
		);
		vec3 fresnel = ( material.specularColor * t2.x + ( vec3( 1.0 ) - material.specularColor ) * t2.y );
		reflectedLight.directSpecular += lightColor * fresnel * LTC_Evaluate( normal, viewDir, position, mInv, rectCoords );
		reflectedLight.directDiffuse += lightColor * material.diffuseColor * LTC_Evaluate( normal, viewDir, position, mat3( 1.0 ), rectCoords );
	}
#endif
void RE_Direct_Physical( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	#ifdef USE_CLEARCOAT
		float dotNLcc = saturate( dot( geometryClearcoatNormal, directLight.direction ) );
		vec3 ccIrradiance = dotNLcc * directLight.color;
		clearcoatSpecularDirect += ccIrradiance * BRDF_GGX_Clearcoat( directLight.direction, geometryViewDir, geometryClearcoatNormal, material );
	#endif
	#ifdef USE_SHEEN
		sheenSpecularDirect += irradiance * BRDF_Sheen( directLight.direction, geometryViewDir, geometryNormal, material.sheenColor, material.sheenRoughness );
	#endif
	reflectedLight.directSpecular += irradiance * BRDF_GGX( directLight.direction, geometryViewDir, geometryNormal, material );
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Physical( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectSpecular_Physical( const in vec3 radiance, const in vec3 irradiance, const in vec3 clearcoatRadiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight) {
	#ifdef USE_CLEARCOAT
		clearcoatSpecularIndirect += clearcoatRadiance * EnvironmentBRDF( geometryClearcoatNormal, geometryViewDir, material.clearcoatF0, material.clearcoatF90, material.clearcoatRoughness );
	#endif
	#ifdef USE_SHEEN
		sheenSpecularIndirect += irradiance * material.sheenColor * IBLSheenBRDF( geometryNormal, geometryViewDir, material.sheenRoughness );
	#endif
	vec3 singleScattering = vec3( 0.0 );
	vec3 multiScattering = vec3( 0.0 );
	vec3 cosineWeightedIrradiance = irradiance * RECIPROCAL_PI;
	#ifdef USE_IRIDESCENCE
		computeMultiscatteringIridescence( geometryNormal, geometryViewDir, material.specularColor, material.specularF90, material.iridescence, material.iridescenceFresnel, material.roughness, singleScattering, multiScattering );
	#else
		computeMultiscattering( geometryNormal, geometryViewDir, material.specularColor, material.specularF90, material.roughness, singleScattering, multiScattering );
	#endif
	vec3 totalScattering = singleScattering + multiScattering;
	vec3 diffuse = material.diffuseColor * ( 1.0 - max( max( totalScattering.r, totalScattering.g ), totalScattering.b ) );
	reflectedLight.indirectSpecular += radiance * singleScattering;
	reflectedLight.indirectSpecular += multiScattering * cosineWeightedIrradiance;
	reflectedLight.indirectDiffuse += diffuse * cosineWeightedIrradiance;
}
#define RE_Direct				RE_Direct_Physical
#define RE_Direct_RectArea		RE_Direct_RectArea_Physical
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Physical
#define RE_IndirectSpecular		RE_IndirectSpecular_Physical
float computeSpecularOcclusion( const in float dotNV, const in float ambientOcclusion, const in float roughness ) {
	return saturate( pow( dotNV + ambientOcclusion, exp2( - 16.0 * roughness - 1.0 ) ) - 1.0 + ambientOcclusion );
}`,UM=`
vec3 geometryPosition = - vViewPosition;
vec3 geometryNormal = normal;
vec3 geometryViewDir = ( isOrthographic ) ? vec3( 0, 0, 1 ) : normalize( vViewPosition );
vec3 geometryClearcoatNormal = vec3( 0.0 );
#ifdef USE_CLEARCOAT
	geometryClearcoatNormal = clearcoatNormal;
#endif
#ifdef USE_IRIDESCENCE
	float dotNVi = saturate( dot( normal, geometryViewDir ) );
	if ( material.iridescenceThickness == 0.0 ) {
		material.iridescence = 0.0;
	} else {
		material.iridescence = saturate( material.iridescence );
	}
	if ( material.iridescence > 0.0 ) {
		material.iridescenceFresnel = evalIridescence( 1.0, material.iridescenceIOR, dotNVi, material.iridescenceThickness, material.specularColor );
		material.iridescenceF0 = Schlick_to_F0( material.iridescenceFresnel, 1.0, dotNVi );
	}
#endif
IncidentLight directLight;
#if ( NUM_POINT_LIGHTS > 0 ) && defined( RE_Direct )
	PointLight pointLight;
	#if defined( USE_SHADOWMAP ) && NUM_POINT_LIGHT_SHADOWS > 0
	PointLightShadow pointLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_POINT_LIGHTS; i ++ ) {
		pointLight = pointLights[ i ];
		getPointLightInfo( pointLight, geometryPosition, directLight );
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_POINT_LIGHT_SHADOWS )
		pointLightShadow = pointLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getPointShadow( pointShadowMap[ i ], pointLightShadow.shadowMapSize, pointLightShadow.shadowIntensity, pointLightShadow.shadowBias, pointLightShadow.shadowRadius, vPointShadowCoord[ i ], pointLightShadow.shadowCameraNear, pointLightShadow.shadowCameraFar ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_SPOT_LIGHTS > 0 ) && defined( RE_Direct )
	SpotLight spotLight;
	vec4 spotColor;
	vec3 spotLightCoord;
	bool inSpotLightMap;
	#if defined( USE_SHADOWMAP ) && NUM_SPOT_LIGHT_SHADOWS > 0
	SpotLightShadow spotLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHTS; i ++ ) {
		spotLight = spotLights[ i ];
		getSpotLightInfo( spotLight, geometryPosition, directLight );
		#if ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS )
		#define SPOT_LIGHT_MAP_INDEX UNROLLED_LOOP_INDEX
		#elif ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
		#define SPOT_LIGHT_MAP_INDEX NUM_SPOT_LIGHT_MAPS
		#else
		#define SPOT_LIGHT_MAP_INDEX ( UNROLLED_LOOP_INDEX - NUM_SPOT_LIGHT_SHADOWS + NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS )
		#endif
		#if ( SPOT_LIGHT_MAP_INDEX < NUM_SPOT_LIGHT_MAPS )
			spotLightCoord = vSpotLightCoord[ i ].xyz / vSpotLightCoord[ i ].w;
			inSpotLightMap = all( lessThan( abs( spotLightCoord * 2. - 1. ), vec3( 1.0 ) ) );
			spotColor = texture2D( spotLightMap[ SPOT_LIGHT_MAP_INDEX ], spotLightCoord.xy );
			directLight.color = inSpotLightMap ? directLight.color * spotColor.rgb : directLight.color;
		#endif
		#undef SPOT_LIGHT_MAP_INDEX
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
		spotLightShadow = spotLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getShadow( spotShadowMap[ i ], spotLightShadow.shadowMapSize, spotLightShadow.shadowIntensity, spotLightShadow.shadowBias, spotLightShadow.shadowRadius, vSpotLightCoord[ i ] ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_DIR_LIGHTS > 0 ) && defined( RE_Direct )
	DirectionalLight directionalLight;
	#if defined( USE_SHADOWMAP ) && NUM_DIR_LIGHT_SHADOWS > 0
	DirectionalLightShadow directionalLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_DIR_LIGHTS; i ++ ) {
		directionalLight = directionalLights[ i ];
		getDirectionalLightInfo( directionalLight, directLight );
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_DIR_LIGHT_SHADOWS )
		directionalLightShadow = directionalLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getShadow( directionalShadowMap[ i ], directionalLightShadow.shadowMapSize, directionalLightShadow.shadowIntensity, directionalLightShadow.shadowBias, directionalLightShadow.shadowRadius, vDirectionalShadowCoord[ i ] ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_RECT_AREA_LIGHTS > 0 ) && defined( RE_Direct_RectArea )
	RectAreaLight rectAreaLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_RECT_AREA_LIGHTS; i ++ ) {
		rectAreaLight = rectAreaLights[ i ];
		RE_Direct_RectArea( rectAreaLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if defined( RE_IndirectDiffuse )
	vec3 iblIrradiance = vec3( 0.0 );
	vec3 irradiance = getAmbientLightIrradiance( ambientLightColor );
	#if defined( USE_LIGHT_PROBES )
		irradiance += getLightProbeIrradiance( lightProbe, geometryNormal );
	#endif
	#if ( NUM_HEMI_LIGHTS > 0 )
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_HEMI_LIGHTS; i ++ ) {
			irradiance += getHemisphereLightIrradiance( hemisphereLights[ i ], geometryNormal );
		}
		#pragma unroll_loop_end
	#endif
#endif
#if defined( RE_IndirectSpecular )
	vec3 radiance = vec3( 0.0 );
	vec3 clearcoatRadiance = vec3( 0.0 );
#endif`,NM=`#if defined( RE_IndirectDiffuse )
	#ifdef USE_LIGHTMAP
		vec4 lightMapTexel = texture2D( lightMap, vLightMapUv );
		vec3 lightMapIrradiance = lightMapTexel.rgb * lightMapIntensity;
		irradiance += lightMapIrradiance;
	#endif
	#if defined( USE_ENVMAP ) && defined( STANDARD ) && defined( ENVMAP_TYPE_CUBE_UV )
		iblIrradiance += getIBLIrradiance( geometryNormal );
	#endif
#endif
#if defined( USE_ENVMAP ) && defined( RE_IndirectSpecular )
	#ifdef USE_ANISOTROPY
		radiance += getIBLAnisotropyRadiance( geometryViewDir, geometryNormal, material.roughness, material.anisotropyB, material.anisotropy );
	#else
		radiance += getIBLRadiance( geometryViewDir, geometryNormal, material.roughness );
	#endif
	#ifdef USE_CLEARCOAT
		clearcoatRadiance += getIBLRadiance( geometryViewDir, geometryClearcoatNormal, material.clearcoatRoughness );
	#endif
#endif`,OM=`#if defined( RE_IndirectDiffuse )
	RE_IndirectDiffuse( irradiance, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
#endif
#if defined( RE_IndirectSpecular )
	RE_IndirectSpecular( radiance, iblIrradiance, clearcoatRadiance, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
#endif`,FM=`#if defined( USE_LOGDEPTHBUF )
	gl_FragDepth = vIsPerspective == 0.0 ? gl_FragCoord.z : log2( vFragDepth ) * logDepthBufFC * 0.5;
#endif`,BM=`#if defined( USE_LOGDEPTHBUF )
	uniform float logDepthBufFC;
	varying float vFragDepth;
	varying float vIsPerspective;
#endif`,kM=`#ifdef USE_LOGDEPTHBUF
	varying float vFragDepth;
	varying float vIsPerspective;
#endif`,zM=`#ifdef USE_LOGDEPTHBUF
	vFragDepth = 1.0 + gl_Position.w;
	vIsPerspective = float( isPerspectiveMatrix( projectionMatrix ) );
#endif`,VM=`#ifdef USE_MAP
	vec4 sampledDiffuseColor = texture2D( map, vMapUv );
	#ifdef DECODE_VIDEO_TEXTURE
		sampledDiffuseColor = sRGBTransferEOTF( sampledDiffuseColor );
	#endif
	diffuseColor *= sampledDiffuseColor;
#endif`,HM=`#ifdef USE_MAP
	uniform sampler2D map;
#endif`,GM=`#if defined( USE_MAP ) || defined( USE_ALPHAMAP )
	#if defined( USE_POINTS_UV )
		vec2 uv = vUv;
	#else
		vec2 uv = ( uvTransform * vec3( gl_PointCoord.x, 1.0 - gl_PointCoord.y, 1 ) ).xy;
	#endif
#endif
#ifdef USE_MAP
	diffuseColor *= texture2D( map, uv );
#endif
#ifdef USE_ALPHAMAP
	diffuseColor.a *= texture2D( alphaMap, uv ).g;
#endif`,WM=`#if defined( USE_POINTS_UV )
	varying vec2 vUv;
#else
	#if defined( USE_MAP ) || defined( USE_ALPHAMAP )
		uniform mat3 uvTransform;
	#endif
#endif
#ifdef USE_MAP
	uniform sampler2D map;
#endif
#ifdef USE_ALPHAMAP
	uniform sampler2D alphaMap;
#endif`,XM=`float metalnessFactor = metalness;
#ifdef USE_METALNESSMAP
	vec4 texelMetalness = texture2D( metalnessMap, vMetalnessMapUv );
	metalnessFactor *= texelMetalness.b;
#endif`,YM=`#ifdef USE_METALNESSMAP
	uniform sampler2D metalnessMap;
#endif`,qM=`#ifdef USE_INSTANCING_MORPH
	float morphTargetInfluences[ MORPHTARGETS_COUNT ];
	float morphTargetBaseInfluence = texelFetch( morphTexture, ivec2( 0, gl_InstanceID ), 0 ).r;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		morphTargetInfluences[i] =  texelFetch( morphTexture, ivec2( i + 1, gl_InstanceID ), 0 ).r;
	}
#endif`,ZM=`#if defined( USE_MORPHCOLORS )
	vColor *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		#if defined( USE_COLOR_ALPHA )
			if ( morphTargetInfluences[ i ] != 0.0 ) vColor += getMorph( gl_VertexID, i, 2 ) * morphTargetInfluences[ i ];
		#elif defined( USE_COLOR )
			if ( morphTargetInfluences[ i ] != 0.0 ) vColor += getMorph( gl_VertexID, i, 2 ).rgb * morphTargetInfluences[ i ];
		#endif
	}
#endif`,$M=`#ifdef USE_MORPHNORMALS
	objectNormal *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		if ( morphTargetInfluences[ i ] != 0.0 ) objectNormal += getMorph( gl_VertexID, i, 1 ).xyz * morphTargetInfluences[ i ];
	}
#endif`,JM=`#ifdef USE_MORPHTARGETS
	#ifndef USE_INSTANCING_MORPH
		uniform float morphTargetBaseInfluence;
		uniform float morphTargetInfluences[ MORPHTARGETS_COUNT ];
	#endif
	uniform sampler2DArray morphTargetsTexture;
	uniform ivec2 morphTargetsTextureSize;
	vec4 getMorph( const in int vertexIndex, const in int morphTargetIndex, const in int offset ) {
		int texelIndex = vertexIndex * MORPHTARGETS_TEXTURE_STRIDE + offset;
		int y = texelIndex / morphTargetsTextureSize.x;
		int x = texelIndex - y * morphTargetsTextureSize.x;
		ivec3 morphUV = ivec3( x, y, morphTargetIndex );
		return texelFetch( morphTargetsTexture, morphUV, 0 );
	}
#endif`,KM=`#ifdef USE_MORPHTARGETS
	transformed *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		if ( morphTargetInfluences[ i ] != 0.0 ) transformed += getMorph( gl_VertexID, i, 0 ).xyz * morphTargetInfluences[ i ];
	}
#endif`,QM=`float faceDirection = gl_FrontFacing ? 1.0 : - 1.0;
#ifdef FLAT_SHADED
	vec3 fdx = dFdx( vViewPosition );
	vec3 fdy = dFdy( vViewPosition );
	vec3 normal = normalize( cross( fdx, fdy ) );
#else
	vec3 normal = normalize( vNormal );
	#ifdef DOUBLE_SIDED
		normal *= faceDirection;
	#endif
#endif
#if defined( USE_NORMALMAP_TANGENTSPACE ) || defined( USE_CLEARCOAT_NORMALMAP ) || defined( USE_ANISOTROPY )
	#ifdef USE_TANGENT
		mat3 tbn = mat3( normalize( vTangent ), normalize( vBitangent ), normal );
	#else
		mat3 tbn = getTangentFrame( - vViewPosition, normal,
		#if defined( USE_NORMALMAP )
			vNormalMapUv
		#elif defined( USE_CLEARCOAT_NORMALMAP )
			vClearcoatNormalMapUv
		#else
			vUv
		#endif
		);
	#endif
	#if defined( DOUBLE_SIDED ) && ! defined( FLAT_SHADED )
		tbn[0] *= faceDirection;
		tbn[1] *= faceDirection;
	#endif
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	#ifdef USE_TANGENT
		mat3 tbn2 = mat3( normalize( vTangent ), normalize( vBitangent ), normal );
	#else
		mat3 tbn2 = getTangentFrame( - vViewPosition, normal, vClearcoatNormalMapUv );
	#endif
	#if defined( DOUBLE_SIDED ) && ! defined( FLAT_SHADED )
		tbn2[0] *= faceDirection;
		tbn2[1] *= faceDirection;
	#endif
#endif
vec3 nonPerturbedNormal = normal;`,jM=`#ifdef USE_NORMALMAP_OBJECTSPACE
	normal = texture2D( normalMap, vNormalMapUv ).xyz * 2.0 - 1.0;
	#ifdef FLIP_SIDED
		normal = - normal;
	#endif
	#ifdef DOUBLE_SIDED
		normal = normal * faceDirection;
	#endif
	normal = normalize( normalMatrix * normal );
#elif defined( USE_NORMALMAP_TANGENTSPACE )
	vec3 mapN = texture2D( normalMap, vNormalMapUv ).xyz * 2.0 - 1.0;
	mapN.xy *= normalScale;
	normal = normalize( tbn * mapN );
#elif defined( USE_BUMPMAP )
	normal = perturbNormalArb( - vViewPosition, normal, dHdxy_fwd(), faceDirection );
#endif`,tS=`#ifndef FLAT_SHADED
	varying vec3 vNormal;
	#ifdef USE_TANGENT
		varying vec3 vTangent;
		varying vec3 vBitangent;
	#endif
#endif`,eS=`#ifndef FLAT_SHADED
	varying vec3 vNormal;
	#ifdef USE_TANGENT
		varying vec3 vTangent;
		varying vec3 vBitangent;
	#endif
#endif`,nS=`#ifndef FLAT_SHADED
	vNormal = normalize( transformedNormal );
	#ifdef USE_TANGENT
		vTangent = normalize( transformedTangent );
		vBitangent = normalize( cross( vNormal, vTangent ) * tangent.w );
	#endif
#endif`,iS=`#ifdef USE_NORMALMAP
	uniform sampler2D normalMap;
	uniform vec2 normalScale;
#endif
#ifdef USE_NORMALMAP_OBJECTSPACE
	uniform mat3 normalMatrix;
#endif
#if ! defined ( USE_TANGENT ) && ( defined ( USE_NORMALMAP_TANGENTSPACE ) || defined ( USE_CLEARCOAT_NORMALMAP ) || defined( USE_ANISOTROPY ) )
	mat3 getTangentFrame( vec3 eye_pos, vec3 surf_norm, vec2 uv ) {
		vec3 q0 = dFdx( eye_pos.xyz );
		vec3 q1 = dFdy( eye_pos.xyz );
		vec2 st0 = dFdx( uv.st );
		vec2 st1 = dFdy( uv.st );
		vec3 N = surf_norm;
		vec3 q1perp = cross( q1, N );
		vec3 q0perp = cross( N, q0 );
		vec3 T = q1perp * st0.x + q0perp * st1.x;
		vec3 B = q1perp * st0.y + q0perp * st1.y;
		float det = max( dot( T, T ), dot( B, B ) );
		float scale = ( det == 0.0 ) ? 0.0 : inversesqrt( det );
		return mat3( T * scale, B * scale, N );
	}
#endif`,sS=`#ifdef USE_CLEARCOAT
	vec3 clearcoatNormal = nonPerturbedNormal;
#endif`,rS=`#ifdef USE_CLEARCOAT_NORMALMAP
	vec3 clearcoatMapN = texture2D( clearcoatNormalMap, vClearcoatNormalMapUv ).xyz * 2.0 - 1.0;
	clearcoatMapN.xy *= clearcoatNormalScale;
	clearcoatNormal = normalize( tbn2 * clearcoatMapN );
#endif`,oS=`#ifdef USE_CLEARCOATMAP
	uniform sampler2D clearcoatMap;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	uniform sampler2D clearcoatNormalMap;
	uniform vec2 clearcoatNormalScale;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	uniform sampler2D clearcoatRoughnessMap;
#endif`,aS=`#ifdef USE_IRIDESCENCEMAP
	uniform sampler2D iridescenceMap;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	uniform sampler2D iridescenceThicknessMap;
#endif`,lS=`#ifdef OPAQUE
diffuseColor.a = 1.0;
#endif
#ifdef USE_TRANSMISSION
diffuseColor.a *= material.transmissionAlpha;
#endif
gl_FragColor = vec4( outgoingLight, diffuseColor.a );`,cS=`vec3 packNormalToRGB( const in vec3 normal ) {
	return normalize( normal ) * 0.5 + 0.5;
}
vec3 unpackRGBToNormal( const in vec3 rgb ) {
	return 2.0 * rgb.xyz - 1.0;
}
const float PackUpscale = 256. / 255.;const float UnpackDownscale = 255. / 256.;const float ShiftRight8 = 1. / 256.;
const float Inv255 = 1. / 255.;
const vec4 PackFactors = vec4( 1.0, 256.0, 256.0 * 256.0, 256.0 * 256.0 * 256.0 );
const vec2 UnpackFactors2 = vec2( UnpackDownscale, 1.0 / PackFactors.g );
const vec3 UnpackFactors3 = vec3( UnpackDownscale / PackFactors.rg, 1.0 / PackFactors.b );
const vec4 UnpackFactors4 = vec4( UnpackDownscale / PackFactors.rgb, 1.0 / PackFactors.a );
vec4 packDepthToRGBA( const in float v ) {
	if( v <= 0.0 )
		return vec4( 0., 0., 0., 0. );
	if( v >= 1.0 )
		return vec4( 1., 1., 1., 1. );
	float vuf;
	float af = modf( v * PackFactors.a, vuf );
	float bf = modf( vuf * ShiftRight8, vuf );
	float gf = modf( vuf * ShiftRight8, vuf );
	return vec4( vuf * Inv255, gf * PackUpscale, bf * PackUpscale, af );
}
vec3 packDepthToRGB( const in float v ) {
	if( v <= 0.0 )
		return vec3( 0., 0., 0. );
	if( v >= 1.0 )
		return vec3( 1., 1., 1. );
	float vuf;
	float bf = modf( v * PackFactors.b, vuf );
	float gf = modf( vuf * ShiftRight8, vuf );
	return vec3( vuf * Inv255, gf * PackUpscale, bf );
}
vec2 packDepthToRG( const in float v ) {
	if( v <= 0.0 )
		return vec2( 0., 0. );
	if( v >= 1.0 )
		return vec2( 1., 1. );
	float vuf;
	float gf = modf( v * 256., vuf );
	return vec2( vuf * Inv255, gf );
}
float unpackRGBAToDepth( const in vec4 v ) {
	return dot( v, UnpackFactors4 );
}
float unpackRGBToDepth( const in vec3 v ) {
	return dot( v, UnpackFactors3 );
}
float unpackRGToDepth( const in vec2 v ) {
	return v.r * UnpackFactors2.r + v.g * UnpackFactors2.g;
}
vec4 pack2HalfToRGBA( const in vec2 v ) {
	vec4 r = vec4( v.x, fract( v.x * 255.0 ), v.y, fract( v.y * 255.0 ) );
	return vec4( r.x - r.y / 255.0, r.y, r.z - r.w / 255.0, r.w );
}
vec2 unpackRGBATo2Half( const in vec4 v ) {
	return vec2( v.x + ( v.y / 255.0 ), v.z + ( v.w / 255.0 ) );
}
float viewZToOrthographicDepth( const in float viewZ, const in float near, const in float far ) {
	return ( viewZ + near ) / ( near - far );
}
float orthographicDepthToViewZ( const in float depth, const in float near, const in float far ) {
	return depth * ( near - far ) - near;
}
float viewZToPerspectiveDepth( const in float viewZ, const in float near, const in float far ) {
	return ( ( near + viewZ ) * far ) / ( ( far - near ) * viewZ );
}
float perspectiveDepthToViewZ( const in float depth, const in float near, const in float far ) {
	return ( near * far ) / ( ( far - near ) * depth - far );
}`,hS=`#ifdef PREMULTIPLIED_ALPHA
	gl_FragColor.rgb *= gl_FragColor.a;
#endif`,uS=`vec4 mvPosition = vec4( transformed, 1.0 );
#ifdef USE_BATCHING
	mvPosition = batchingMatrix * mvPosition;
#endif
#ifdef USE_INSTANCING
	mvPosition = instanceMatrix * mvPosition;
#endif
mvPosition = modelViewMatrix * mvPosition;
gl_Position = projectionMatrix * mvPosition;`,fS=`#ifdef DITHERING
	gl_FragColor.rgb = dithering( gl_FragColor.rgb );
#endif`,dS=`#ifdef DITHERING
	vec3 dithering( vec3 color ) {
		float grid_position = rand( gl_FragCoord.xy );
		vec3 dither_shift_RGB = vec3( 0.25 / 255.0, -0.25 / 255.0, 0.25 / 255.0 );
		dither_shift_RGB = mix( 2.0 * dither_shift_RGB, -2.0 * dither_shift_RGB, grid_position );
		return color + dither_shift_RGB;
	}
#endif`,pS=`float roughnessFactor = roughness;
#ifdef USE_ROUGHNESSMAP
	vec4 texelRoughness = texture2D( roughnessMap, vRoughnessMapUv );
	roughnessFactor *= texelRoughness.g;
#endif`,mS=`#ifdef USE_ROUGHNESSMAP
	uniform sampler2D roughnessMap;
#endif`,gS=`#if NUM_SPOT_LIGHT_COORDS > 0
	varying vec4 vSpotLightCoord[ NUM_SPOT_LIGHT_COORDS ];
#endif
#if NUM_SPOT_LIGHT_MAPS > 0
	uniform sampler2D spotLightMap[ NUM_SPOT_LIGHT_MAPS ];
#endif
#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
		uniform sampler2D directionalShadowMap[ NUM_DIR_LIGHT_SHADOWS ];
		varying vec4 vDirectionalShadowCoord[ NUM_DIR_LIGHT_SHADOWS ];
		struct DirectionalLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform DirectionalLightShadow directionalLightShadows[ NUM_DIR_LIGHT_SHADOWS ];
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
		uniform sampler2D spotShadowMap[ NUM_SPOT_LIGHT_SHADOWS ];
		struct SpotLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform SpotLightShadow spotLightShadows[ NUM_SPOT_LIGHT_SHADOWS ];
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		uniform sampler2D pointShadowMap[ NUM_POINT_LIGHT_SHADOWS ];
		varying vec4 vPointShadowCoord[ NUM_POINT_LIGHT_SHADOWS ];
		struct PointLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
			float shadowCameraNear;
			float shadowCameraFar;
		};
		uniform PointLightShadow pointLightShadows[ NUM_POINT_LIGHT_SHADOWS ];
	#endif
	float texture2DCompare( sampler2D depths, vec2 uv, float compare ) {
		return step( compare, unpackRGBAToDepth( texture2D( depths, uv ) ) );
	}
	vec2 texture2DDistribution( sampler2D shadow, vec2 uv ) {
		return unpackRGBATo2Half( texture2D( shadow, uv ) );
	}
	float VSMShadow (sampler2D shadow, vec2 uv, float compare ){
		float occlusion = 1.0;
		vec2 distribution = texture2DDistribution( shadow, uv );
		float hard_shadow = step( compare , distribution.x );
		if (hard_shadow != 1.0 ) {
			float distance = compare - distribution.x ;
			float variance = max( 0.00000, distribution.y * distribution.y );
			float softness_probability = variance / (variance + distance * distance );			softness_probability = clamp( ( softness_probability - 0.3 ) / ( 0.95 - 0.3 ), 0.0, 1.0 );			occlusion = clamp( max( hard_shadow, softness_probability ), 0.0, 1.0 );
		}
		return occlusion;
	}
	float getShadow( sampler2D shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord ) {
		float shadow = 1.0;
		shadowCoord.xyz /= shadowCoord.w;
		shadowCoord.z += shadowBias;
		bool inFrustum = shadowCoord.x >= 0.0 && shadowCoord.x <= 1.0 && shadowCoord.y >= 0.0 && shadowCoord.y <= 1.0;
		bool frustumTest = inFrustum && shadowCoord.z <= 1.0;
		if ( frustumTest ) {
		#if defined( SHADOWMAP_TYPE_PCF )
			vec2 texelSize = vec2( 1.0 ) / shadowMapSize;
			float dx0 = - texelSize.x * shadowRadius;
			float dy0 = - texelSize.y * shadowRadius;
			float dx1 = + texelSize.x * shadowRadius;
			float dy1 = + texelSize.y * shadowRadius;
			float dx2 = dx0 / 2.0;
			float dy2 = dy0 / 2.0;
			float dx3 = dx1 / 2.0;
			float dy3 = dy1 / 2.0;
			shadow = (
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx0, dy0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx1, dy0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx2, dy2 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy2 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx3, dy2 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx0, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx2, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy, shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx3, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx1, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx2, dy3 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy3 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx3, dy3 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx0, dy1 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy1 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx1, dy1 ), shadowCoord.z )
			) * ( 1.0 / 17.0 );
		#elif defined( SHADOWMAP_TYPE_PCF_SOFT )
			vec2 texelSize = vec2( 1.0 ) / shadowMapSize;
			float dx = texelSize.x;
			float dy = texelSize.y;
			vec2 uv = shadowCoord.xy;
			vec2 f = fract( uv * shadowMapSize + 0.5 );
			uv -= f * texelSize;
			shadow = (
				texture2DCompare( shadowMap, uv, shadowCoord.z ) +
				texture2DCompare( shadowMap, uv + vec2( dx, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, uv + vec2( 0.0, dy ), shadowCoord.z ) +
				texture2DCompare( shadowMap, uv + texelSize, shadowCoord.z ) +
				mix( texture2DCompare( shadowMap, uv + vec2( -dx, 0.0 ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, 0.0 ), shadowCoord.z ),
					 f.x ) +
				mix( texture2DCompare( shadowMap, uv + vec2( -dx, dy ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, dy ), shadowCoord.z ),
					 f.x ) +
				mix( texture2DCompare( shadowMap, uv + vec2( 0.0, -dy ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( 0.0, 2.0 * dy ), shadowCoord.z ),
					 f.y ) +
				mix( texture2DCompare( shadowMap, uv + vec2( dx, -dy ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( dx, 2.0 * dy ), shadowCoord.z ),
					 f.y ) +
				mix( mix( texture2DCompare( shadowMap, uv + vec2( -dx, -dy ), shadowCoord.z ),
						  texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, -dy ), shadowCoord.z ),
						  f.x ),
					 mix( texture2DCompare( shadowMap, uv + vec2( -dx, 2.0 * dy ), shadowCoord.z ),
						  texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, 2.0 * dy ), shadowCoord.z ),
						  f.x ),
					 f.y )
			) * ( 1.0 / 9.0 );
		#elif defined( SHADOWMAP_TYPE_VSM )
			shadow = VSMShadow( shadowMap, shadowCoord.xy, shadowCoord.z );
		#else
			shadow = texture2DCompare( shadowMap, shadowCoord.xy, shadowCoord.z );
		#endif
		}
		return mix( 1.0, shadow, shadowIntensity );
	}
	vec2 cubeToUV( vec3 v, float texelSizeY ) {
		vec3 absV = abs( v );
		float scaleToCube = 1.0 / max( absV.x, max( absV.y, absV.z ) );
		absV *= scaleToCube;
		v *= scaleToCube * ( 1.0 - 2.0 * texelSizeY );
		vec2 planar = v.xy;
		float almostATexel = 1.5 * texelSizeY;
		float almostOne = 1.0 - almostATexel;
		if ( absV.z >= almostOne ) {
			if ( v.z > 0.0 )
				planar.x = 4.0 - v.x;
		} else if ( absV.x >= almostOne ) {
			float signX = sign( v.x );
			planar.x = v.z * signX + 2.0 * signX;
		} else if ( absV.y >= almostOne ) {
			float signY = sign( v.y );
			planar.x = v.x + 2.0 * signY + 2.0;
			planar.y = v.z * signY - 2.0;
		}
		return vec2( 0.125, 0.25 ) * planar + vec2( 0.375, 0.75 );
	}
	float getPointShadow( sampler2D shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord, float shadowCameraNear, float shadowCameraFar ) {
		float shadow = 1.0;
		vec3 lightToPosition = shadowCoord.xyz;
		
		float lightToPositionLength = length( lightToPosition );
		if ( lightToPositionLength - shadowCameraFar <= 0.0 && lightToPositionLength - shadowCameraNear >= 0.0 ) {
			float dp = ( lightToPositionLength - shadowCameraNear ) / ( shadowCameraFar - shadowCameraNear );			dp += shadowBias;
			vec3 bd3D = normalize( lightToPosition );
			vec2 texelSize = vec2( 1.0 ) / ( shadowMapSize * vec2( 4.0, 2.0 ) );
			#if defined( SHADOWMAP_TYPE_PCF ) || defined( SHADOWMAP_TYPE_PCF_SOFT ) || defined( SHADOWMAP_TYPE_VSM )
				vec2 offset = vec2( - 1, 1 ) * shadowRadius * texelSize.y;
				shadow = (
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xyy, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yyy, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xyx, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yyx, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xxy, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yxy, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xxx, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yxx, texelSize.y ), dp )
				) * ( 1.0 / 9.0 );
			#else
				shadow = texture2DCompare( shadowMap, cubeToUV( bd3D, texelSize.y ), dp );
			#endif
		}
		return mix( 1.0, shadow, shadowIntensity );
	}
#endif`,_S=`#if NUM_SPOT_LIGHT_COORDS > 0
	uniform mat4 spotLightMatrix[ NUM_SPOT_LIGHT_COORDS ];
	varying vec4 vSpotLightCoord[ NUM_SPOT_LIGHT_COORDS ];
#endif
#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
		uniform mat4 directionalShadowMatrix[ NUM_DIR_LIGHT_SHADOWS ];
		varying vec4 vDirectionalShadowCoord[ NUM_DIR_LIGHT_SHADOWS ];
		struct DirectionalLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform DirectionalLightShadow directionalLightShadows[ NUM_DIR_LIGHT_SHADOWS ];
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
		struct SpotLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform SpotLightShadow spotLightShadows[ NUM_SPOT_LIGHT_SHADOWS ];
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		uniform mat4 pointShadowMatrix[ NUM_POINT_LIGHT_SHADOWS ];
		varying vec4 vPointShadowCoord[ NUM_POINT_LIGHT_SHADOWS ];
		struct PointLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
			float shadowCameraNear;
			float shadowCameraFar;
		};
		uniform PointLightShadow pointLightShadows[ NUM_POINT_LIGHT_SHADOWS ];
	#endif
#endif`,vS=`#if ( defined( USE_SHADOWMAP ) && ( NUM_DIR_LIGHT_SHADOWS > 0 || NUM_POINT_LIGHT_SHADOWS > 0 ) ) || ( NUM_SPOT_LIGHT_COORDS > 0 )
	vec3 shadowWorldNormal = inverseTransformDirection( transformedNormal, viewMatrix );
	vec4 shadowWorldPosition;
#endif
#if defined( USE_SHADOWMAP )
	#if NUM_DIR_LIGHT_SHADOWS > 0
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_DIR_LIGHT_SHADOWS; i ++ ) {
			shadowWorldPosition = worldPosition + vec4( shadowWorldNormal * directionalLightShadows[ i ].shadowNormalBias, 0 );
			vDirectionalShadowCoord[ i ] = directionalShadowMatrix[ i ] * shadowWorldPosition;
		}
		#pragma unroll_loop_end
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_POINT_LIGHT_SHADOWS; i ++ ) {
			shadowWorldPosition = worldPosition + vec4( shadowWorldNormal * pointLightShadows[ i ].shadowNormalBias, 0 );
			vPointShadowCoord[ i ] = pointShadowMatrix[ i ] * shadowWorldPosition;
		}
		#pragma unroll_loop_end
	#endif
#endif
#if NUM_SPOT_LIGHT_COORDS > 0
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHT_COORDS; i ++ ) {
		shadowWorldPosition = worldPosition;
		#if ( defined( USE_SHADOWMAP ) && UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
			shadowWorldPosition.xyz += shadowWorldNormal * spotLightShadows[ i ].shadowNormalBias;
		#endif
		vSpotLightCoord[ i ] = spotLightMatrix[ i ] * shadowWorldPosition;
	}
	#pragma unroll_loop_end
#endif`,xS=`float getShadowMask() {
	float shadow = 1.0;
	#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
	DirectionalLightShadow directionalLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_DIR_LIGHT_SHADOWS; i ++ ) {
		directionalLight = directionalLightShadows[ i ];
		shadow *= receiveShadow ? getShadow( directionalShadowMap[ i ], directionalLight.shadowMapSize, directionalLight.shadowIntensity, directionalLight.shadowBias, directionalLight.shadowRadius, vDirectionalShadowCoord[ i ] ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
	SpotLightShadow spotLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHT_SHADOWS; i ++ ) {
		spotLight = spotLightShadows[ i ];
		shadow *= receiveShadow ? getShadow( spotShadowMap[ i ], spotLight.shadowMapSize, spotLight.shadowIntensity, spotLight.shadowBias, spotLight.shadowRadius, vSpotLightCoord[ i ] ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
	PointLightShadow pointLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_POINT_LIGHT_SHADOWS; i ++ ) {
		pointLight = pointLightShadows[ i ];
		shadow *= receiveShadow ? getPointShadow( pointShadowMap[ i ], pointLight.shadowMapSize, pointLight.shadowIntensity, pointLight.shadowBias, pointLight.shadowRadius, vPointShadowCoord[ i ], pointLight.shadowCameraNear, pointLight.shadowCameraFar ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#endif
	return shadow;
}`,yS=`#ifdef USE_SKINNING
	mat4 boneMatX = getBoneMatrix( skinIndex.x );
	mat4 boneMatY = getBoneMatrix( skinIndex.y );
	mat4 boneMatZ = getBoneMatrix( skinIndex.z );
	mat4 boneMatW = getBoneMatrix( skinIndex.w );
#endif`,MS=`#ifdef USE_SKINNING
	uniform mat4 bindMatrix;
	uniform mat4 bindMatrixInverse;
	uniform highp sampler2D boneTexture;
	mat4 getBoneMatrix( const in float i ) {
		int size = textureSize( boneTexture, 0 ).x;
		int j = int( i ) * 4;
		int x = j % size;
		int y = j / size;
		vec4 v1 = texelFetch( boneTexture, ivec2( x, y ), 0 );
		vec4 v2 = texelFetch( boneTexture, ivec2( x + 1, y ), 0 );
		vec4 v3 = texelFetch( boneTexture, ivec2( x + 2, y ), 0 );
		vec4 v4 = texelFetch( boneTexture, ivec2( x + 3, y ), 0 );
		return mat4( v1, v2, v3, v4 );
	}
#endif`,SS=`#ifdef USE_SKINNING
	vec4 skinVertex = bindMatrix * vec4( transformed, 1.0 );
	vec4 skinned = vec4( 0.0 );
	skinned += boneMatX * skinVertex * skinWeight.x;
	skinned += boneMatY * skinVertex * skinWeight.y;
	skinned += boneMatZ * skinVertex * skinWeight.z;
	skinned += boneMatW * skinVertex * skinWeight.w;
	transformed = ( bindMatrixInverse * skinned ).xyz;
#endif`,bS=`#ifdef USE_SKINNING
	mat4 skinMatrix = mat4( 0.0 );
	skinMatrix += skinWeight.x * boneMatX;
	skinMatrix += skinWeight.y * boneMatY;
	skinMatrix += skinWeight.z * boneMatZ;
	skinMatrix += skinWeight.w * boneMatW;
	skinMatrix = bindMatrixInverse * skinMatrix * bindMatrix;
	objectNormal = vec4( skinMatrix * vec4( objectNormal, 0.0 ) ).xyz;
	#ifdef USE_TANGENT
		objectTangent = vec4( skinMatrix * vec4( objectTangent, 0.0 ) ).xyz;
	#endif
#endif`,wS=`float specularStrength;
#ifdef USE_SPECULARMAP
	vec4 texelSpecular = texture2D( specularMap, vSpecularMapUv );
	specularStrength = texelSpecular.r;
#else
	specularStrength = 1.0;
#endif`,TS=`#ifdef USE_SPECULARMAP
	uniform sampler2D specularMap;
#endif`,ES=`#if defined( TONE_MAPPING )
	gl_FragColor.rgb = toneMapping( gl_FragColor.rgb );
#endif`,AS=`#ifndef saturate
#define saturate( a ) clamp( a, 0.0, 1.0 )
#endif
uniform float toneMappingExposure;
vec3 LinearToneMapping( vec3 color ) {
	return saturate( toneMappingExposure * color );
}
vec3 ReinhardToneMapping( vec3 color ) {
	color *= toneMappingExposure;
	return saturate( color / ( vec3( 1.0 ) + color ) );
}
vec3 CineonToneMapping( vec3 color ) {
	color *= toneMappingExposure;
	color = max( vec3( 0.0 ), color - 0.004 );
	return pow( ( color * ( 6.2 * color + 0.5 ) ) / ( color * ( 6.2 * color + 1.7 ) + 0.06 ), vec3( 2.2 ) );
}
vec3 RRTAndODTFit( vec3 v ) {
	vec3 a = v * ( v + 0.0245786 ) - 0.000090537;
	vec3 b = v * ( 0.983729 * v + 0.4329510 ) + 0.238081;
	return a / b;
}
vec3 ACESFilmicToneMapping( vec3 color ) {
	const mat3 ACESInputMat = mat3(
		vec3( 0.59719, 0.07600, 0.02840 ),		vec3( 0.35458, 0.90834, 0.13383 ),
		vec3( 0.04823, 0.01566, 0.83777 )
	);
	const mat3 ACESOutputMat = mat3(
		vec3(  1.60475, -0.10208, -0.00327 ),		vec3( -0.53108,  1.10813, -0.07276 ),
		vec3( -0.07367, -0.00605,  1.07602 )
	);
	color *= toneMappingExposure / 0.6;
	color = ACESInputMat * color;
	color = RRTAndODTFit( color );
	color = ACESOutputMat * color;
	return saturate( color );
}
const mat3 LINEAR_REC2020_TO_LINEAR_SRGB = mat3(
	vec3( 1.6605, - 0.1246, - 0.0182 ),
	vec3( - 0.5876, 1.1329, - 0.1006 ),
	vec3( - 0.0728, - 0.0083, 1.1187 )
);
const mat3 LINEAR_SRGB_TO_LINEAR_REC2020 = mat3(
	vec3( 0.6274, 0.0691, 0.0164 ),
	vec3( 0.3293, 0.9195, 0.0880 ),
	vec3( 0.0433, 0.0113, 0.8956 )
);
vec3 agxDefaultContrastApprox( vec3 x ) {
	vec3 x2 = x * x;
	vec3 x4 = x2 * x2;
	return + 15.5 * x4 * x2
		- 40.14 * x4 * x
		+ 31.96 * x4
		- 6.868 * x2 * x
		+ 0.4298 * x2
		+ 0.1191 * x
		- 0.00232;
}
vec3 AgXToneMapping( vec3 color ) {
	const mat3 AgXInsetMatrix = mat3(
		vec3( 0.856627153315983, 0.137318972929847, 0.11189821299995 ),
		vec3( 0.0951212405381588, 0.761241990602591, 0.0767994186031903 ),
		vec3( 0.0482516061458583, 0.101439036467562, 0.811302368396859 )
	);
	const mat3 AgXOutsetMatrix = mat3(
		vec3( 1.1271005818144368, - 0.1413297634984383, - 0.14132976349843826 ),
		vec3( - 0.11060664309660323, 1.157823702216272, - 0.11060664309660294 ),
		vec3( - 0.016493938717834573, - 0.016493938717834257, 1.2519364065950405 )
	);
	const float AgxMinEv = - 12.47393;	const float AgxMaxEv = 4.026069;
	color *= toneMappingExposure;
	color = LINEAR_SRGB_TO_LINEAR_REC2020 * color;
	color = AgXInsetMatrix * color;
	color = max( color, 1e-10 );	color = log2( color );
	color = ( color - AgxMinEv ) / ( AgxMaxEv - AgxMinEv );
	color = clamp( color, 0.0, 1.0 );
	color = agxDefaultContrastApprox( color );
	color = AgXOutsetMatrix * color;
	color = pow( max( vec3( 0.0 ), color ), vec3( 2.2 ) );
	color = LINEAR_REC2020_TO_LINEAR_SRGB * color;
	color = clamp( color, 0.0, 1.0 );
	return color;
}
vec3 NeutralToneMapping( vec3 color ) {
	const float StartCompression = 0.8 - 0.04;
	const float Desaturation = 0.15;
	color *= toneMappingExposure;
	float x = min( color.r, min( color.g, color.b ) );
	float offset = x < 0.08 ? x - 6.25 * x * x : 0.04;
	color -= offset;
	float peak = max( color.r, max( color.g, color.b ) );
	if ( peak < StartCompression ) return color;
	float d = 1. - StartCompression;
	float newPeak = 1. - d * d / ( peak + d - StartCompression );
	color *= newPeak / peak;
	float g = 1. - 1. / ( Desaturation * ( peak - newPeak ) + 1. );
	return mix( color, vec3( newPeak ), g );
}
vec3 CustomToneMapping( vec3 color ) { return color; }`,CS=`#ifdef USE_TRANSMISSION
	material.transmission = transmission;
	material.transmissionAlpha = 1.0;
	material.thickness = thickness;
	material.attenuationDistance = attenuationDistance;
	material.attenuationColor = attenuationColor;
	#ifdef USE_TRANSMISSIONMAP
		material.transmission *= texture2D( transmissionMap, vTransmissionMapUv ).r;
	#endif
	#ifdef USE_THICKNESSMAP
		material.thickness *= texture2D( thicknessMap, vThicknessMapUv ).g;
	#endif
	vec3 pos = vWorldPosition;
	vec3 v = normalize( cameraPosition - pos );
	vec3 n = inverseTransformDirection( normal, viewMatrix );
	vec4 transmitted = getIBLVolumeRefraction(
		n, v, material.roughness, material.diffuseColor, material.specularColor, material.specularF90,
		pos, modelMatrix, viewMatrix, projectionMatrix, material.dispersion, material.ior, material.thickness,
		material.attenuationColor, material.attenuationDistance );
	material.transmissionAlpha = mix( material.transmissionAlpha, transmitted.a, material.transmission );
	totalDiffuse = mix( totalDiffuse, transmitted.rgb, material.transmission );
#endif`,RS=`#ifdef USE_TRANSMISSION
	uniform float transmission;
	uniform float thickness;
	uniform float attenuationDistance;
	uniform vec3 attenuationColor;
	#ifdef USE_TRANSMISSIONMAP
		uniform sampler2D transmissionMap;
	#endif
	#ifdef USE_THICKNESSMAP
		uniform sampler2D thicknessMap;
	#endif
	uniform vec2 transmissionSamplerSize;
	uniform sampler2D transmissionSamplerMap;
	uniform mat4 modelMatrix;
	uniform mat4 projectionMatrix;
	varying vec3 vWorldPosition;
	float w0( float a ) {
		return ( 1.0 / 6.0 ) * ( a * ( a * ( - a + 3.0 ) - 3.0 ) + 1.0 );
	}
	float w1( float a ) {
		return ( 1.0 / 6.0 ) * ( a *  a * ( 3.0 * a - 6.0 ) + 4.0 );
	}
	float w2( float a ){
		return ( 1.0 / 6.0 ) * ( a * ( a * ( - 3.0 * a + 3.0 ) + 3.0 ) + 1.0 );
	}
	float w3( float a ) {
		return ( 1.0 / 6.0 ) * ( a * a * a );
	}
	float g0( float a ) {
		return w0( a ) + w1( a );
	}
	float g1( float a ) {
		return w2( a ) + w3( a );
	}
	float h0( float a ) {
		return - 1.0 + w1( a ) / ( w0( a ) + w1( a ) );
	}
	float h1( float a ) {
		return 1.0 + w3( a ) / ( w2( a ) + w3( a ) );
	}
	vec4 bicubic( sampler2D tex, vec2 uv, vec4 texelSize, float lod ) {
		uv = uv * texelSize.zw + 0.5;
		vec2 iuv = floor( uv );
		vec2 fuv = fract( uv );
		float g0x = g0( fuv.x );
		float g1x = g1( fuv.x );
		float h0x = h0( fuv.x );
		float h1x = h1( fuv.x );
		float h0y = h0( fuv.y );
		float h1y = h1( fuv.y );
		vec2 p0 = ( vec2( iuv.x + h0x, iuv.y + h0y ) - 0.5 ) * texelSize.xy;
		vec2 p1 = ( vec2( iuv.x + h1x, iuv.y + h0y ) - 0.5 ) * texelSize.xy;
		vec2 p2 = ( vec2( iuv.x + h0x, iuv.y + h1y ) - 0.5 ) * texelSize.xy;
		vec2 p3 = ( vec2( iuv.x + h1x, iuv.y + h1y ) - 0.5 ) * texelSize.xy;
		return g0( fuv.y ) * ( g0x * textureLod( tex, p0, lod ) + g1x * textureLod( tex, p1, lod ) ) +
			g1( fuv.y ) * ( g0x * textureLod( tex, p2, lod ) + g1x * textureLod( tex, p3, lod ) );
	}
	vec4 textureBicubic( sampler2D sampler, vec2 uv, float lod ) {
		vec2 fLodSize = vec2( textureSize( sampler, int( lod ) ) );
		vec2 cLodSize = vec2( textureSize( sampler, int( lod + 1.0 ) ) );
		vec2 fLodSizeInv = 1.0 / fLodSize;
		vec2 cLodSizeInv = 1.0 / cLodSize;
		vec4 fSample = bicubic( sampler, uv, vec4( fLodSizeInv, fLodSize ), floor( lod ) );
		vec4 cSample = bicubic( sampler, uv, vec4( cLodSizeInv, cLodSize ), ceil( lod ) );
		return mix( fSample, cSample, fract( lod ) );
	}
	vec3 getVolumeTransmissionRay( const in vec3 n, const in vec3 v, const in float thickness, const in float ior, const in mat4 modelMatrix ) {
		vec3 refractionVector = refract( - v, normalize( n ), 1.0 / ior );
		vec3 modelScale;
		modelScale.x = length( vec3( modelMatrix[ 0 ].xyz ) );
		modelScale.y = length( vec3( modelMatrix[ 1 ].xyz ) );
		modelScale.z = length( vec3( modelMatrix[ 2 ].xyz ) );
		return normalize( refractionVector ) * thickness * modelScale;
	}
	float applyIorToRoughness( const in float roughness, const in float ior ) {
		return roughness * clamp( ior * 2.0 - 2.0, 0.0, 1.0 );
	}
	vec4 getTransmissionSample( const in vec2 fragCoord, const in float roughness, const in float ior ) {
		float lod = log2( transmissionSamplerSize.x ) * applyIorToRoughness( roughness, ior );
		return textureBicubic( transmissionSamplerMap, fragCoord.xy, lod );
	}
	vec3 volumeAttenuation( const in float transmissionDistance, const in vec3 attenuationColor, const in float attenuationDistance ) {
		if ( isinf( attenuationDistance ) ) {
			return vec3( 1.0 );
		} else {
			vec3 attenuationCoefficient = -log( attenuationColor ) / attenuationDistance;
			vec3 transmittance = exp( - attenuationCoefficient * transmissionDistance );			return transmittance;
		}
	}
	vec4 getIBLVolumeRefraction( const in vec3 n, const in vec3 v, const in float roughness, const in vec3 diffuseColor,
		const in vec3 specularColor, const in float specularF90, const in vec3 position, const in mat4 modelMatrix,
		const in mat4 viewMatrix, const in mat4 projMatrix, const in float dispersion, const in float ior, const in float thickness,
		const in vec3 attenuationColor, const in float attenuationDistance ) {
		vec4 transmittedLight;
		vec3 transmittance;
		#ifdef USE_DISPERSION
			float halfSpread = ( ior - 1.0 ) * 0.025 * dispersion;
			vec3 iors = vec3( ior - halfSpread, ior, ior + halfSpread );
			for ( int i = 0; i < 3; i ++ ) {
				vec3 transmissionRay = getVolumeTransmissionRay( n, v, thickness, iors[ i ], modelMatrix );
				vec3 refractedRayExit = position + transmissionRay;
		
				vec4 ndcPos = projMatrix * viewMatrix * vec4( refractedRayExit, 1.0 );
				vec2 refractionCoords = ndcPos.xy / ndcPos.w;
				refractionCoords += 1.0;
				refractionCoords /= 2.0;
		
				vec4 transmissionSample = getTransmissionSample( refractionCoords, roughness, iors[ i ] );
				transmittedLight[ i ] = transmissionSample[ i ];
				transmittedLight.a += transmissionSample.a;
				transmittance[ i ] = diffuseColor[ i ] * volumeAttenuation( length( transmissionRay ), attenuationColor, attenuationDistance )[ i ];
			}
			transmittedLight.a /= 3.0;
		
		#else
		
			vec3 transmissionRay = getVolumeTransmissionRay( n, v, thickness, ior, modelMatrix );
			vec3 refractedRayExit = position + transmissionRay;
			vec4 ndcPos = projMatrix * viewMatrix * vec4( refractedRayExit, 1.0 );
			vec2 refractionCoords = ndcPos.xy / ndcPos.w;
			refractionCoords += 1.0;
			refractionCoords /= 2.0;
			transmittedLight = getTransmissionSample( refractionCoords, roughness, ior );
			transmittance = diffuseColor * volumeAttenuation( length( transmissionRay ), attenuationColor, attenuationDistance );
		
		#endif
		vec3 attenuatedColor = transmittance * transmittedLight.rgb;
		vec3 F = EnvironmentBRDF( n, v, specularColor, specularF90, roughness );
		float transmittanceFactor = ( transmittance.r + transmittance.g + transmittance.b ) / 3.0;
		return vec4( ( 1.0 - F ) * attenuatedColor, 1.0 - ( 1.0 - transmittedLight.a ) * transmittanceFactor );
	}
#endif`,PS=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	varying vec2 vUv;
#endif
#ifdef USE_MAP
	varying vec2 vMapUv;
#endif
#ifdef USE_ALPHAMAP
	varying vec2 vAlphaMapUv;
#endif
#ifdef USE_LIGHTMAP
	varying vec2 vLightMapUv;
#endif
#ifdef USE_AOMAP
	varying vec2 vAoMapUv;
#endif
#ifdef USE_BUMPMAP
	varying vec2 vBumpMapUv;
#endif
#ifdef USE_NORMALMAP
	varying vec2 vNormalMapUv;
#endif
#ifdef USE_EMISSIVEMAP
	varying vec2 vEmissiveMapUv;
#endif
#ifdef USE_METALNESSMAP
	varying vec2 vMetalnessMapUv;
#endif
#ifdef USE_ROUGHNESSMAP
	varying vec2 vRoughnessMapUv;
#endif
#ifdef USE_ANISOTROPYMAP
	varying vec2 vAnisotropyMapUv;
#endif
#ifdef USE_CLEARCOATMAP
	varying vec2 vClearcoatMapUv;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	varying vec2 vClearcoatNormalMapUv;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	varying vec2 vClearcoatRoughnessMapUv;
#endif
#ifdef USE_IRIDESCENCEMAP
	varying vec2 vIridescenceMapUv;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	varying vec2 vIridescenceThicknessMapUv;
#endif
#ifdef USE_SHEEN_COLORMAP
	varying vec2 vSheenColorMapUv;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	varying vec2 vSheenRoughnessMapUv;
#endif
#ifdef USE_SPECULARMAP
	varying vec2 vSpecularMapUv;
#endif
#ifdef USE_SPECULAR_COLORMAP
	varying vec2 vSpecularColorMapUv;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	varying vec2 vSpecularIntensityMapUv;
#endif
#ifdef USE_TRANSMISSIONMAP
	uniform mat3 transmissionMapTransform;
	varying vec2 vTransmissionMapUv;
#endif
#ifdef USE_THICKNESSMAP
	uniform mat3 thicknessMapTransform;
	varying vec2 vThicknessMapUv;
#endif`,IS=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	varying vec2 vUv;
#endif
#ifdef USE_MAP
	uniform mat3 mapTransform;
	varying vec2 vMapUv;
#endif
#ifdef USE_ALPHAMAP
	uniform mat3 alphaMapTransform;
	varying vec2 vAlphaMapUv;
#endif
#ifdef USE_LIGHTMAP
	uniform mat3 lightMapTransform;
	varying vec2 vLightMapUv;
#endif
#ifdef USE_AOMAP
	uniform mat3 aoMapTransform;
	varying vec2 vAoMapUv;
#endif
#ifdef USE_BUMPMAP
	uniform mat3 bumpMapTransform;
	varying vec2 vBumpMapUv;
#endif
#ifdef USE_NORMALMAP
	uniform mat3 normalMapTransform;
	varying vec2 vNormalMapUv;
#endif
#ifdef USE_DISPLACEMENTMAP
	uniform mat3 displacementMapTransform;
	varying vec2 vDisplacementMapUv;
#endif
#ifdef USE_EMISSIVEMAP
	uniform mat3 emissiveMapTransform;
	varying vec2 vEmissiveMapUv;
#endif
#ifdef USE_METALNESSMAP
	uniform mat3 metalnessMapTransform;
	varying vec2 vMetalnessMapUv;
#endif
#ifdef USE_ROUGHNESSMAP
	uniform mat3 roughnessMapTransform;
	varying vec2 vRoughnessMapUv;
#endif
#ifdef USE_ANISOTROPYMAP
	uniform mat3 anisotropyMapTransform;
	varying vec2 vAnisotropyMapUv;
#endif
#ifdef USE_CLEARCOATMAP
	uniform mat3 clearcoatMapTransform;
	varying vec2 vClearcoatMapUv;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	uniform mat3 clearcoatNormalMapTransform;
	varying vec2 vClearcoatNormalMapUv;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	uniform mat3 clearcoatRoughnessMapTransform;
	varying vec2 vClearcoatRoughnessMapUv;
#endif
#ifdef USE_SHEEN_COLORMAP
	uniform mat3 sheenColorMapTransform;
	varying vec2 vSheenColorMapUv;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	uniform mat3 sheenRoughnessMapTransform;
	varying vec2 vSheenRoughnessMapUv;
#endif
#ifdef USE_IRIDESCENCEMAP
	uniform mat3 iridescenceMapTransform;
	varying vec2 vIridescenceMapUv;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	uniform mat3 iridescenceThicknessMapTransform;
	varying vec2 vIridescenceThicknessMapUv;
#endif
#ifdef USE_SPECULARMAP
	uniform mat3 specularMapTransform;
	varying vec2 vSpecularMapUv;
#endif
#ifdef USE_SPECULAR_COLORMAP
	uniform mat3 specularColorMapTransform;
	varying vec2 vSpecularColorMapUv;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	uniform mat3 specularIntensityMapTransform;
	varying vec2 vSpecularIntensityMapUv;
#endif
#ifdef USE_TRANSMISSIONMAP
	uniform mat3 transmissionMapTransform;
	varying vec2 vTransmissionMapUv;
#endif
#ifdef USE_THICKNESSMAP
	uniform mat3 thicknessMapTransform;
	varying vec2 vThicknessMapUv;
#endif`,LS=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	vUv = vec3( uv, 1 ).xy;
#endif
#ifdef USE_MAP
	vMapUv = ( mapTransform * vec3( MAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ALPHAMAP
	vAlphaMapUv = ( alphaMapTransform * vec3( ALPHAMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_LIGHTMAP
	vLightMapUv = ( lightMapTransform * vec3( LIGHTMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_AOMAP
	vAoMapUv = ( aoMapTransform * vec3( AOMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_BUMPMAP
	vBumpMapUv = ( bumpMapTransform * vec3( BUMPMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_NORMALMAP
	vNormalMapUv = ( normalMapTransform * vec3( NORMALMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_DISPLACEMENTMAP
	vDisplacementMapUv = ( displacementMapTransform * vec3( DISPLACEMENTMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_EMISSIVEMAP
	vEmissiveMapUv = ( emissiveMapTransform * vec3( EMISSIVEMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_METALNESSMAP
	vMetalnessMapUv = ( metalnessMapTransform * vec3( METALNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ROUGHNESSMAP
	vRoughnessMapUv = ( roughnessMapTransform * vec3( ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ANISOTROPYMAP
	vAnisotropyMapUv = ( anisotropyMapTransform * vec3( ANISOTROPYMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOATMAP
	vClearcoatMapUv = ( clearcoatMapTransform * vec3( CLEARCOATMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	vClearcoatNormalMapUv = ( clearcoatNormalMapTransform * vec3( CLEARCOAT_NORMALMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	vClearcoatRoughnessMapUv = ( clearcoatRoughnessMapTransform * vec3( CLEARCOAT_ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_IRIDESCENCEMAP
	vIridescenceMapUv = ( iridescenceMapTransform * vec3( IRIDESCENCEMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	vIridescenceThicknessMapUv = ( iridescenceThicknessMapTransform * vec3( IRIDESCENCE_THICKNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SHEEN_COLORMAP
	vSheenColorMapUv = ( sheenColorMapTransform * vec3( SHEEN_COLORMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	vSheenRoughnessMapUv = ( sheenRoughnessMapTransform * vec3( SHEEN_ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULARMAP
	vSpecularMapUv = ( specularMapTransform * vec3( SPECULARMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULAR_COLORMAP
	vSpecularColorMapUv = ( specularColorMapTransform * vec3( SPECULAR_COLORMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	vSpecularIntensityMapUv = ( specularIntensityMapTransform * vec3( SPECULAR_INTENSITYMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_TRANSMISSIONMAP
	vTransmissionMapUv = ( transmissionMapTransform * vec3( TRANSMISSIONMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_THICKNESSMAP
	vThicknessMapUv = ( thicknessMapTransform * vec3( THICKNESSMAP_UV, 1 ) ).xy;
#endif`,DS=`#if defined( USE_ENVMAP ) || defined( DISTANCE ) || defined ( USE_SHADOWMAP ) || defined ( USE_TRANSMISSION ) || NUM_SPOT_LIGHT_COORDS > 0
	vec4 worldPosition = vec4( transformed, 1.0 );
	#ifdef USE_BATCHING
		worldPosition = batchingMatrix * worldPosition;
	#endif
	#ifdef USE_INSTANCING
		worldPosition = instanceMatrix * worldPosition;
	#endif
	worldPosition = modelMatrix * worldPosition;
#endif`,US=`varying vec2 vUv;
uniform mat3 uvTransform;
void main() {
	vUv = ( uvTransform * vec3( uv, 1 ) ).xy;
	gl_Position = vec4( position.xy, 1.0, 1.0 );
}`,NS=`uniform sampler2D t2D;
uniform float backgroundIntensity;
varying vec2 vUv;
void main() {
	vec4 texColor = texture2D( t2D, vUv );
	#ifdef DECODE_VIDEO_TEXTURE
		texColor = vec4( mix( pow( texColor.rgb * 0.9478672986 + vec3( 0.0521327014 ), vec3( 2.4 ) ), texColor.rgb * 0.0773993808, vec3( lessThanEqual( texColor.rgb, vec3( 0.04045 ) ) ) ), texColor.w );
	#endif
	texColor.rgb *= backgroundIntensity;
	gl_FragColor = texColor;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,OS=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
	gl_Position.z = gl_Position.w;
}`,FS=`#ifdef ENVMAP_TYPE_CUBE
	uniform samplerCube envMap;
#elif defined( ENVMAP_TYPE_CUBE_UV )
	uniform sampler2D envMap;
#endif
uniform float flipEnvMap;
uniform float backgroundBlurriness;
uniform float backgroundIntensity;
uniform mat3 backgroundRotation;
varying vec3 vWorldDirection;
#include <cube_uv_reflection_fragment>
void main() {
	#ifdef ENVMAP_TYPE_CUBE
		vec4 texColor = textureCube( envMap, backgroundRotation * vec3( flipEnvMap * vWorldDirection.x, vWorldDirection.yz ) );
	#elif defined( ENVMAP_TYPE_CUBE_UV )
		vec4 texColor = textureCubeUV( envMap, backgroundRotation * vWorldDirection, backgroundBlurriness );
	#else
		vec4 texColor = vec4( 0.0, 0.0, 0.0, 1.0 );
	#endif
	texColor.rgb *= backgroundIntensity;
	gl_FragColor = texColor;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,BS=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
	gl_Position.z = gl_Position.w;
}`,kS=`uniform samplerCube tCube;
uniform float tFlip;
uniform float opacity;
varying vec3 vWorldDirection;
void main() {
	vec4 texColor = textureCube( tCube, vec3( tFlip * vWorldDirection.x, vWorldDirection.yz ) );
	gl_FragColor = texColor;
	gl_FragColor.a *= opacity;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,zS=`#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
varying vec2 vHighPrecisionZW;
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <skinbase_vertex>
	#include <morphinstance_vertex>
	#ifdef USE_DISPLACEMENTMAP
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vHighPrecisionZW = gl_Position.zw;
}`,VS=`#if DEPTH_PACKING == 3200
	uniform float opacity;
#endif
#include <common>
#include <packing>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
varying vec2 vHighPrecisionZW;
void main() {
	vec4 diffuseColor = vec4( 1.0 );
	#include <clipping_planes_fragment>
	#if DEPTH_PACKING == 3200
		diffuseColor.a = opacity;
	#endif
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <logdepthbuf_fragment>
	float fragCoordZ = 0.5 * vHighPrecisionZW[0] / vHighPrecisionZW[1] + 0.5;
	#if DEPTH_PACKING == 3200
		gl_FragColor = vec4( vec3( 1.0 - fragCoordZ ), opacity );
	#elif DEPTH_PACKING == 3201
		gl_FragColor = packDepthToRGBA( fragCoordZ );
	#elif DEPTH_PACKING == 3202
		gl_FragColor = vec4( packDepthToRGB( fragCoordZ ), 1.0 );
	#elif DEPTH_PACKING == 3203
		gl_FragColor = vec4( packDepthToRG( fragCoordZ ), 0.0, 1.0 );
	#endif
}`,HS=`#define DISTANCE
varying vec3 vWorldPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <skinbase_vertex>
	#include <morphinstance_vertex>
	#ifdef USE_DISPLACEMENTMAP
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <worldpos_vertex>
	#include <clipping_planes_vertex>
	vWorldPosition = worldPosition.xyz;
}`,GS=`#define DISTANCE
uniform vec3 referencePosition;
uniform float nearDistance;
uniform float farDistance;
varying vec3 vWorldPosition;
#include <common>
#include <packing>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <clipping_planes_pars_fragment>
void main () {
	vec4 diffuseColor = vec4( 1.0 );
	#include <clipping_planes_fragment>
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	float dist = length( vWorldPosition - referencePosition );
	dist = ( dist - nearDistance ) / ( farDistance - nearDistance );
	dist = saturate( dist );
	gl_FragColor = packDepthToRGBA( dist );
}`,WS=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
}`,XS=`uniform sampler2D tEquirect;
varying vec3 vWorldDirection;
#include <common>
void main() {
	vec3 direction = normalize( vWorldDirection );
	vec2 sampleUV = equirectUv( direction );
	gl_FragColor = texture2D( tEquirect, sampleUV );
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,YS=`uniform float scale;
attribute float lineDistance;
varying float vLineDistance;
#include <common>
#include <uv_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	vLineDistance = scale * lineDistance;
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
}`,qS=`uniform vec3 diffuse;
uniform float opacity;
uniform float dashSize;
uniform float totalSize;
varying float vLineDistance;
#include <common>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	if ( mod( vLineDistance, totalSize ) > dashSize ) {
		discard;
	}
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
}`,ZS=`#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#if defined ( USE_ENVMAP ) || defined ( USE_SKINNING )
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinbase_vertex>
		#include <skinnormal_vertex>
		#include <defaultnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <fog_vertex>
}`,$S=`uniform vec3 diffuse;
uniform float opacity;
#ifndef FLAT_SHADED
	varying vec3 vNormal;
#endif
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	#ifdef USE_LIGHTMAP
		vec4 lightMapTexel = texture2D( lightMap, vLightMapUv );
		reflectedLight.indirectDiffuse += lightMapTexel.rgb * lightMapIntensity * RECIPROCAL_PI;
	#else
		reflectedLight.indirectDiffuse += vec3( 1.0 );
	#endif
	#include <aomap_fragment>
	reflectedLight.indirectDiffuse *= diffuseColor.rgb;
	vec3 outgoingLight = reflectedLight.indirectDiffuse;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,JS=`#define LAMBERT
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,KS=`#define LAMBERT
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float opacity;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_lambert_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_lambert_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + totalEmissiveRadiance;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,QS=`#define MATCAP
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <color_pars_vertex>
#include <displacementmap_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
	vViewPosition = - mvPosition.xyz;
}`,jS=`#define MATCAP
uniform vec3 diffuse;
uniform float opacity;
uniform sampler2D matcap;
varying vec3 vViewPosition;
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <normal_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	vec3 viewDir = normalize( vViewPosition );
	vec3 x = normalize( vec3( viewDir.z, 0.0, - viewDir.x ) );
	vec3 y = cross( viewDir, x );
	vec2 uv = vec2( dot( x, normal ), dot( y, normal ) ) * 0.495 + 0.5;
	#ifdef USE_MATCAP
		vec4 matcapColor = texture2D( matcap, uv );
	#else
		vec4 matcapColor = vec4( vec3( mix( 0.2, 0.8, uv.y ) ), 1.0 );
	#endif
	vec3 outgoingLight = diffuseColor.rgb * matcapColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,tb=`#define NORMAL
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	varying vec3 vViewPosition;
#endif
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	vViewPosition = - mvPosition.xyz;
#endif
}`,eb=`#define NORMAL
uniform float opacity;
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	varying vec3 vViewPosition;
#endif
#include <packing>
#include <uv_pars_fragment>
#include <normal_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( 0.0, 0.0, 0.0, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	gl_FragColor = vec4( packNormalToRGB( normal ), diffuseColor.a );
	#ifdef OPAQUE
		gl_FragColor.a = 1.0;
	#endif
}`,nb=`#define PHONG
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,ib=`#define PHONG
uniform vec3 diffuse;
uniform vec3 emissive;
uniform vec3 specular;
uniform float shininess;
uniform float opacity;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_phong_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_phong_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + reflectedLight.directSpecular + reflectedLight.indirectSpecular + totalEmissiveRadiance;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,sb=`#define STANDARD
varying vec3 vViewPosition;
#ifdef USE_TRANSMISSION
	varying vec3 vWorldPosition;
#endif
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
#ifdef USE_TRANSMISSION
	vWorldPosition = worldPosition.xyz;
#endif
}`,rb=`#define STANDARD
#ifdef PHYSICAL
	#define IOR
	#define USE_SPECULAR
#endif
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float roughness;
uniform float metalness;
uniform float opacity;
#ifdef IOR
	uniform float ior;
#endif
#ifdef USE_SPECULAR
	uniform float specularIntensity;
	uniform vec3 specularColor;
	#ifdef USE_SPECULAR_COLORMAP
		uniform sampler2D specularColorMap;
	#endif
	#ifdef USE_SPECULAR_INTENSITYMAP
		uniform sampler2D specularIntensityMap;
	#endif
#endif
#ifdef USE_CLEARCOAT
	uniform float clearcoat;
	uniform float clearcoatRoughness;
#endif
#ifdef USE_DISPERSION
	uniform float dispersion;
#endif
#ifdef USE_IRIDESCENCE
	uniform float iridescence;
	uniform float iridescenceIOR;
	uniform float iridescenceThicknessMinimum;
	uniform float iridescenceThicknessMaximum;
#endif
#ifdef USE_SHEEN
	uniform vec3 sheenColor;
	uniform float sheenRoughness;
	#ifdef USE_SHEEN_COLORMAP
		uniform sampler2D sheenColorMap;
	#endif
	#ifdef USE_SHEEN_ROUGHNESSMAP
		uniform sampler2D sheenRoughnessMap;
	#endif
#endif
#ifdef USE_ANISOTROPY
	uniform vec2 anisotropyVector;
	#ifdef USE_ANISOTROPYMAP
		uniform sampler2D anisotropyMap;
	#endif
#endif
varying vec3 vViewPosition;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <iridescence_fragment>
#include <cube_uv_reflection_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_physical_pars_fragment>
#include <fog_pars_fragment>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_physical_pars_fragment>
#include <transmission_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <clearcoat_pars_fragment>
#include <iridescence_pars_fragment>
#include <roughnessmap_pars_fragment>
#include <metalnessmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <roughnessmap_fragment>
	#include <metalnessmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <clearcoat_normal_fragment_begin>
	#include <clearcoat_normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_physical_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 totalDiffuse = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse;
	vec3 totalSpecular = reflectedLight.directSpecular + reflectedLight.indirectSpecular;
	#include <transmission_fragment>
	vec3 outgoingLight = totalDiffuse + totalSpecular + totalEmissiveRadiance;
	#ifdef USE_SHEEN
		float sheenEnergyComp = 1.0 - 0.157 * max3( material.sheenColor );
		outgoingLight = outgoingLight * sheenEnergyComp + sheenSpecularDirect + sheenSpecularIndirect;
	#endif
	#ifdef USE_CLEARCOAT
		float dotNVcc = saturate( dot( geometryClearcoatNormal, geometryViewDir ) );
		vec3 Fcc = F_Schlick( material.clearcoatF0, material.clearcoatF90, dotNVcc );
		outgoingLight = outgoingLight * ( 1.0 - material.clearcoat * Fcc ) + ( clearcoatSpecularDirect + clearcoatSpecularIndirect ) * material.clearcoat;
	#endif
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,ob=`#define TOON
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,ab=`#define TOON
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float opacity;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <gradientmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_toon_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_toon_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + totalEmissiveRadiance;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,lb=`uniform float size;
uniform float scale;
#include <common>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
#ifdef USE_POINTS_UV
	varying vec2 vUv;
	uniform mat3 uvTransform;
#endif
void main() {
	#ifdef USE_POINTS_UV
		vUv = ( uvTransform * vec3( uv, 1 ) ).xy;
	#endif
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <project_vertex>
	gl_PointSize = size;
	#ifdef USE_SIZEATTENUATION
		bool isPerspective = isPerspectiveMatrix( projectionMatrix );
		if ( isPerspective ) gl_PointSize *= ( scale / - mvPosition.z );
	#endif
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <worldpos_vertex>
	#include <fog_vertex>
}`,cb=`uniform vec3 diffuse;
uniform float opacity;
#include <common>
#include <color_pars_fragment>
#include <map_particle_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_particle_fragment>
	#include <color_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
}`,hb=`#include <common>
#include <batching_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <shadowmap_pars_vertex>
void main() {
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,ub=`uniform vec3 color;
uniform float opacity;
#include <common>
#include <packing>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <logdepthbuf_pars_fragment>
#include <shadowmap_pars_fragment>
#include <shadowmask_pars_fragment>
void main() {
	#include <logdepthbuf_fragment>
	gl_FragColor = vec4( color, opacity * ( 1.0 - getShadowMask() ) );
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
}`,fb=`uniform float rotation;
uniform vec2 center;
#include <common>
#include <uv_pars_vertex>
#include <fog_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	vec4 mvPosition = modelViewMatrix[ 3 ];
	vec2 scale = vec2( length( modelMatrix[ 0 ].xyz ), length( modelMatrix[ 1 ].xyz ) );
	#ifndef USE_SIZEATTENUATION
		bool isPerspective = isPerspectiveMatrix( projectionMatrix );
		if ( isPerspective ) scale *= - mvPosition.z;
	#endif
	vec2 alignedPosition = ( position.xy - ( center - vec2( 0.5 ) ) ) * scale;
	vec2 rotatedPosition;
	rotatedPosition.x = cos( rotation ) * alignedPosition.x - sin( rotation ) * alignedPosition.y;
	rotatedPosition.y = sin( rotation ) * alignedPosition.x + cos( rotation ) * alignedPosition.y;
	mvPosition.xy += rotatedPosition;
	gl_Position = projectionMatrix * mvPosition;
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
}`,db=`uniform vec3 diffuse;
uniform float opacity;
#include <common>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
}`,ce={alphahash_fragment:Ny,alphahash_pars_fragment:Oy,alphamap_fragment:Fy,alphamap_pars_fragment:By,alphatest_fragment:ky,alphatest_pars_fragment:zy,aomap_fragment:Vy,aomap_pars_fragment:Hy,batching_pars_vertex:Gy,batching_vertex:Wy,begin_vertex:Xy,beginnormal_vertex:Yy,bsdfs:qy,iridescence_fragment:Zy,bumpmap_pars_fragment:$y,clipping_planes_fragment:Jy,clipping_planes_pars_fragment:Ky,clipping_planes_pars_vertex:Qy,clipping_planes_vertex:jy,color_fragment:tM,color_pars_fragment:eM,color_pars_vertex:nM,color_vertex:iM,common:sM,cube_uv_reflection_fragment:rM,defaultnormal_vertex:oM,displacementmap_pars_vertex:aM,displacementmap_vertex:lM,emissivemap_fragment:cM,emissivemap_pars_fragment:hM,colorspace_fragment:uM,colorspace_pars_fragment:fM,envmap_fragment:dM,envmap_common_pars_fragment:pM,envmap_pars_fragment:mM,envmap_pars_vertex:gM,envmap_physical_pars_fragment:AM,envmap_vertex:_M,fog_vertex:vM,fog_pars_vertex:xM,fog_fragment:yM,fog_pars_fragment:MM,gradientmap_pars_fragment:SM,lightmap_pars_fragment:bM,lights_lambert_fragment:wM,lights_lambert_pars_fragment:TM,lights_pars_begin:EM,lights_toon_fragment:CM,lights_toon_pars_fragment:RM,lights_phong_fragment:PM,lights_phong_pars_fragment:IM,lights_physical_fragment:LM,lights_physical_pars_fragment:DM,lights_fragment_begin:UM,lights_fragment_maps:NM,lights_fragment_end:OM,logdepthbuf_fragment:FM,logdepthbuf_pars_fragment:BM,logdepthbuf_pars_vertex:kM,logdepthbuf_vertex:zM,map_fragment:VM,map_pars_fragment:HM,map_particle_fragment:GM,map_particle_pars_fragment:WM,metalnessmap_fragment:XM,metalnessmap_pars_fragment:YM,morphinstance_vertex:qM,morphcolor_vertex:ZM,morphnormal_vertex:$M,morphtarget_pars_vertex:JM,morphtarget_vertex:KM,normal_fragment_begin:QM,normal_fragment_maps:jM,normal_pars_fragment:tS,normal_pars_vertex:eS,normal_vertex:nS,normalmap_pars_fragment:iS,clearcoat_normal_fragment_begin:sS,clearcoat_normal_fragment_maps:rS,clearcoat_pars_fragment:oS,iridescence_pars_fragment:aS,opaque_fragment:lS,packing:cS,premultiplied_alpha_fragment:hS,project_vertex:uS,dithering_fragment:fS,dithering_pars_fragment:dS,roughnessmap_fragment:pS,roughnessmap_pars_fragment:mS,shadowmap_pars_fragment:gS,shadowmap_pars_vertex:_S,shadowmap_vertex:vS,shadowmask_pars_fragment:xS,skinbase_vertex:yS,skinning_pars_vertex:MS,skinning_vertex:SS,skinnormal_vertex:bS,specularmap_fragment:wS,specularmap_pars_fragment:TS,tonemapping_fragment:ES,tonemapping_pars_fragment:AS,transmission_fragment:CS,transmission_pars_fragment:RS,uv_pars_fragment:PS,uv_pars_vertex:IS,uv_vertex:LS,worldpos_vertex:DS,background_vert:US,background_frag:NS,backgroundCube_vert:OS,backgroundCube_frag:FS,cube_vert:BS,cube_frag:kS,depth_vert:zS,depth_frag:VS,distanceRGBA_vert:HS,distanceRGBA_frag:GS,equirect_vert:WS,equirect_frag:XS,linedashed_vert:YS,linedashed_frag:qS,meshbasic_vert:ZS,meshbasic_frag:$S,meshlambert_vert:JS,meshlambert_frag:KS,meshmatcap_vert:QS,meshmatcap_frag:jS,meshnormal_vert:tb,meshnormal_frag:eb,meshphong_vert:nb,meshphong_frag:ib,meshphysical_vert:sb,meshphysical_frag:rb,meshtoon_vert:ob,meshtoon_frag:ab,points_vert:lb,points_frag:cb,shadow_vert:hb,shadow_frag:ub,sprite_vert:fb,sprite_frag:db},Pt={common:{diffuse:{value:new se(16777215)},opacity:{value:1},map:{value:null},mapTransform:{value:new oe},alphaMap:{value:null},alphaMapTransform:{value:new oe},alphaTest:{value:0}},specularmap:{specularMap:{value:null},specularMapTransform:{value:new oe}},envmap:{envMap:{value:null},envMapRotation:{value:new oe},flipEnvMap:{value:-1},reflectivity:{value:1},ior:{value:1.5},refractionRatio:{value:.98}},aomap:{aoMap:{value:null},aoMapIntensity:{value:1},aoMapTransform:{value:new oe}},lightmap:{lightMap:{value:null},lightMapIntensity:{value:1},lightMapTransform:{value:new oe}},bumpmap:{bumpMap:{value:null},bumpMapTransform:{value:new oe},bumpScale:{value:1}},normalmap:{normalMap:{value:null},normalMapTransform:{value:new oe},normalScale:{value:new vt(1,1)}},displacementmap:{displacementMap:{value:null},displacementMapTransform:{value:new oe},displacementScale:{value:1},displacementBias:{value:0}},emissivemap:{emissiveMap:{value:null},emissiveMapTransform:{value:new oe}},metalnessmap:{metalnessMap:{value:null},metalnessMapTransform:{value:new oe}},roughnessmap:{roughnessMap:{value:null},roughnessMapTransform:{value:new oe}},gradientmap:{gradientMap:{value:null}},fog:{fogDensity:{value:25e-5},fogNear:{value:1},fogFar:{value:2e3},fogColor:{value:new se(16777215)}},lights:{ambientLightColor:{value:[]},lightProbe:{value:[]},directionalLights:{value:[],properties:{direction:{},color:{}}},directionalLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{}}},directionalShadowMap:{value:[]},directionalShadowMatrix:{value:[]},spotLights:{value:[],properties:{color:{},position:{},direction:{},distance:{},coneCos:{},penumbraCos:{},decay:{}}},spotLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{}}},spotLightMap:{value:[]},spotShadowMap:{value:[]},spotLightMatrix:{value:[]},pointLights:{value:[],properties:{color:{},position:{},decay:{},distance:{}}},pointLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{},shadowCameraNear:{},shadowCameraFar:{}}},pointShadowMap:{value:[]},pointShadowMatrix:{value:[]},hemisphereLights:{value:[],properties:{direction:{},skyColor:{},groundColor:{}}},rectAreaLights:{value:[],properties:{color:{},position:{},width:{},height:{}}},ltc_1:{value:null},ltc_2:{value:null}},points:{diffuse:{value:new se(16777215)},opacity:{value:1},size:{value:1},scale:{value:1},map:{value:null},alphaMap:{value:null},alphaMapTransform:{value:new oe},alphaTest:{value:0},uvTransform:{value:new oe}},sprite:{diffuse:{value:new se(16777215)},opacity:{value:1},center:{value:new vt(.5,.5)},rotation:{value:0},map:{value:null},mapTransform:{value:new oe},alphaMap:{value:null},alphaMapTransform:{value:new oe},alphaTest:{value:0}}},Oi={basic:{uniforms:Dn([Pt.common,Pt.specularmap,Pt.envmap,Pt.aomap,Pt.lightmap,Pt.fog]),vertexShader:ce.meshbasic_vert,fragmentShader:ce.meshbasic_frag},lambert:{uniforms:Dn([Pt.common,Pt.specularmap,Pt.envmap,Pt.aomap,Pt.lightmap,Pt.emissivemap,Pt.bumpmap,Pt.normalmap,Pt.displacementmap,Pt.fog,Pt.lights,{emissive:{value:new se(0)}}]),vertexShader:ce.meshlambert_vert,fragmentShader:ce.meshlambert_frag},phong:{uniforms:Dn([Pt.common,Pt.specularmap,Pt.envmap,Pt.aomap,Pt.lightmap,Pt.emissivemap,Pt.bumpmap,Pt.normalmap,Pt.displacementmap,Pt.fog,Pt.lights,{emissive:{value:new se(0)},specular:{value:new se(1118481)},shininess:{value:30}}]),vertexShader:ce.meshphong_vert,fragmentShader:ce.meshphong_frag},standard:{uniforms:Dn([Pt.common,Pt.envmap,Pt.aomap,Pt.lightmap,Pt.emissivemap,Pt.bumpmap,Pt.normalmap,Pt.displacementmap,Pt.roughnessmap,Pt.metalnessmap,Pt.fog,Pt.lights,{emissive:{value:new se(0)},roughness:{value:1},metalness:{value:0},envMapIntensity:{value:1}}]),vertexShader:ce.meshphysical_vert,fragmentShader:ce.meshphysical_frag},toon:{uniforms:Dn([Pt.common,Pt.aomap,Pt.lightmap,Pt.emissivemap,Pt.bumpmap,Pt.normalmap,Pt.displacementmap,Pt.gradientmap,Pt.fog,Pt.lights,{emissive:{value:new se(0)}}]),vertexShader:ce.meshtoon_vert,fragmentShader:ce.meshtoon_frag},matcap:{uniforms:Dn([Pt.common,Pt.bumpmap,Pt.normalmap,Pt.displacementmap,Pt.fog,{matcap:{value:null}}]),vertexShader:ce.meshmatcap_vert,fragmentShader:ce.meshmatcap_frag},points:{uniforms:Dn([Pt.points,Pt.fog]),vertexShader:ce.points_vert,fragmentShader:ce.points_frag},dashed:{uniforms:Dn([Pt.common,Pt.fog,{scale:{value:1},dashSize:{value:1},totalSize:{value:2}}]),vertexShader:ce.linedashed_vert,fragmentShader:ce.linedashed_frag},depth:{uniforms:Dn([Pt.common,Pt.displacementmap]),vertexShader:ce.depth_vert,fragmentShader:ce.depth_frag},normal:{uniforms:Dn([Pt.common,Pt.bumpmap,Pt.normalmap,Pt.displacementmap,{opacity:{value:1}}]),vertexShader:ce.meshnormal_vert,fragmentShader:ce.meshnormal_frag},sprite:{uniforms:Dn([Pt.sprite,Pt.fog]),vertexShader:ce.sprite_vert,fragmentShader:ce.sprite_frag},background:{uniforms:{uvTransform:{value:new oe},t2D:{value:null},backgroundIntensity:{value:1}},vertexShader:ce.background_vert,fragmentShader:ce.background_frag},backgroundCube:{uniforms:{envMap:{value:null},flipEnvMap:{value:-1},backgroundBlurriness:{value:0},backgroundIntensity:{value:1},backgroundRotation:{value:new oe}},vertexShader:ce.backgroundCube_vert,fragmentShader:ce.backgroundCube_frag},cube:{uniforms:{tCube:{value:null},tFlip:{value:-1},opacity:{value:1}},vertexShader:ce.cube_vert,fragmentShader:ce.cube_frag},equirect:{uniforms:{tEquirect:{value:null}},vertexShader:ce.equirect_vert,fragmentShader:ce.equirect_frag},distanceRGBA:{uniforms:Dn([Pt.common,Pt.displacementmap,{referencePosition:{value:new B},nearDistance:{value:1},farDistance:{value:1e3}}]),vertexShader:ce.distanceRGBA_vert,fragmentShader:ce.distanceRGBA_frag},shadow:{uniforms:Dn([Pt.lights,Pt.fog,{color:{value:new se(0)},opacity:{value:1}}]),vertexShader:ce.shadow_vert,fragmentShader:ce.shadow_frag}};Oi.physical={uniforms:Dn([Oi.standard.uniforms,{clearcoat:{value:0},clearcoatMap:{value:null},clearcoatMapTransform:{value:new oe},clearcoatNormalMap:{value:null},clearcoatNormalMapTransform:{value:new oe},clearcoatNormalScale:{value:new vt(1,1)},clearcoatRoughness:{value:0},clearcoatRoughnessMap:{value:null},clearcoatRoughnessMapTransform:{value:new oe},dispersion:{value:0},iridescence:{value:0},iridescenceMap:{value:null},iridescenceMapTransform:{value:new oe},iridescenceIOR:{value:1.3},iridescenceThicknessMinimum:{value:100},iridescenceThicknessMaximum:{value:400},iridescenceThicknessMap:{value:null},iridescenceThicknessMapTransform:{value:new oe},sheen:{value:0},sheenColor:{value:new se(0)},sheenColorMap:{value:null},sheenColorMapTransform:{value:new oe},sheenRoughness:{value:1},sheenRoughnessMap:{value:null},sheenRoughnessMapTransform:{value:new oe},transmission:{value:0},transmissionMap:{value:null},transmissionMapTransform:{value:new oe},transmissionSamplerSize:{value:new vt},transmissionSamplerMap:{value:null},thickness:{value:0},thicknessMap:{value:null},thicknessMapTransform:{value:new oe},attenuationDistance:{value:0},attenuationColor:{value:new se(0)},specularColor:{value:new se(1,1,1)},specularColorMap:{value:null},specularColorMapTransform:{value:new oe},specularIntensity:{value:1},specularIntensityMap:{value:null},specularIntensityMapTransform:{value:new oe},anisotropyVector:{value:new vt},anisotropyMap:{value:null},anisotropyMapTransform:{value:new oe}}]),vertexShader:ce.meshphysical_vert,fragmentShader:ce.meshphysical_frag};var lc={r:0,b:0,g:0},dr=new mi,pb=new Ce;function mb(s,t,e,n,i,r,o){let a=new se(0),l=r===!0?0:1,c,h,u=null,f=0,d=null;function g(S){let y=S.isScene===!0?S.background:null;return y&&y.isTexture&&(y=(S.backgroundBlurriness>0?e:t).get(y)),y}function _(S){let y=!1,v=g(S);v===null?p(a,l):v&&v.isColor&&(p(v,1),y=!0);let E=s.xr.getEnvironmentBlendMode();E==="additive"?n.buffers.color.setClear(0,0,0,1,o):E==="alpha-blend"&&n.buffers.color.setClear(0,0,0,0,o),(s.autoClear||y)&&(n.buffers.depth.setTest(!0),n.buffers.depth.setMask(!0),n.buffers.color.setMask(!0),s.clear(s.autoClearColor,s.autoClearDepth,s.autoClearStencil))}function m(S,y){let v=g(y);v&&(v.isCubeTexture||v.mapping===Zc)?(h===void 0&&(h=new ve(new wr(1,1,1),new je({name:"BackgroundCubeMaterial",uniforms:Ro(Oi.backgroundCube.uniforms),vertexShader:Oi.backgroundCube.vertexShader,fragmentShader:Oi.backgroundCube.fragmentShader,side:wn,depthTest:!1,depthWrite:!1,fog:!1})),h.geometry.deleteAttribute("normal"),h.geometry.deleteAttribute("uv"),h.onBeforeRender=function(E,A,T){this.matrixWorld.copyPosition(T.matrixWorld)},Object.defineProperty(h.material,"envMap",{get:function(){return this.uniforms.envMap.value}}),i.update(h)),dr.copy(y.backgroundRotation),dr.x*=-1,dr.y*=-1,dr.z*=-1,v.isCubeTexture&&v.isRenderTargetTexture===!1&&(dr.y*=-1,dr.z*=-1),h.material.uniforms.envMap.value=v,h.material.uniforms.flipEnvMap.value=v.isCubeTexture&&v.isRenderTargetTexture===!1?-1:1,h.material.uniforms.backgroundBlurriness.value=y.backgroundBlurriness,h.material.uniforms.backgroundIntensity.value=y.backgroundIntensity,h.material.uniforms.backgroundRotation.value.setFromMatrix4(pb.makeRotationFromEuler(dr)),h.material.toneMapped=ge.getTransfer(v.colorSpace)!==we,(u!==v||f!==v.version||d!==s.toneMapping)&&(h.material.needsUpdate=!0,u=v,f=v.version,d=s.toneMapping),h.layers.enableAll(),S.unshift(h,h.geometry,h.material,0,0,null)):v&&v.isTexture&&(c===void 0&&(c=new ve(new Tr(2,2),new je({name:"BackgroundMaterial",uniforms:Ro(Oi.background.uniforms),vertexShader:Oi.background.vertexShader,fragmentShader:Oi.background.fragmentShader,side:Bs,depthTest:!1,depthWrite:!1,fog:!1})),c.geometry.deleteAttribute("normal"),Object.defineProperty(c.material,"map",{get:function(){return this.uniforms.t2D.value}}),i.update(c)),c.material.uniforms.t2D.value=v,c.material.uniforms.backgroundIntensity.value=y.backgroundIntensity,c.material.toneMapped=ge.getTransfer(v.colorSpace)!==we,v.matrixAutoUpdate===!0&&v.updateMatrix(),c.material.uniforms.uvTransform.value.copy(v.matrix),(u!==v||f!==v.version||d!==s.toneMapping)&&(c.material.needsUpdate=!0,u=v,f=v.version,d=s.toneMapping),c.layers.enableAll(),S.unshift(c,c.geometry,c.material,0,0,null))}function p(S,y){S.getRGB(lc,W_(s)),n.buffers.color.setClear(lc.r,lc.g,lc.b,y,o)}return{getClearColor:function(){return a},setClearColor:function(S,y=1){a.set(S),l=y,p(a,l)},getClearAlpha:function(){return l},setClearAlpha:function(S){l=S,p(a,l)},render:_,addToRenderList:m}}function gb(s,t){let e=s.getParameter(s.MAX_VERTEX_ATTRIBS),n={},i=f(null),r=i,o=!1;function a(x,L,U,F,z){let q=!1,H=u(F,U,L);r!==H&&(r=H,c(r.object)),q=d(x,F,U,z),q&&g(x,F,U,z),z!==null&&t.update(z,s.ELEMENT_ARRAY_BUFFER),(q||o)&&(o=!1,v(x,L,U,F),z!==null&&s.bindBuffer(s.ELEMENT_ARRAY_BUFFER,t.get(z).buffer))}function l(){return s.createVertexArray()}function c(x){return s.bindVertexArray(x)}function h(x){return s.deleteVertexArray(x)}function u(x,L,U){let F=U.wireframe===!0,z=n[x.id];z===void 0&&(z={},n[x.id]=z);let q=z[L.id];q===void 0&&(q={},z[L.id]=q);let H=q[F];return H===void 0&&(H=f(l()),q[F]=H),H}function f(x){let L=[],U=[],F=[];for(let z=0;z<e;z++)L[z]=0,U[z]=0,F[z]=0;return{geometry:null,program:null,wireframe:!1,newAttributes:L,enabledAttributes:U,attributeDivisors:F,object:x,attributes:{},index:null}}function d(x,L,U,F){let z=r.attributes,q=L.attributes,H=0,W=U.getAttributes();for(let V in W)if(W[V].location>=0){let I=z[V],at=q[V];if(at===void 0&&(V==="instanceMatrix"&&x.instanceMatrix&&(at=x.instanceMatrix),V==="instanceColor"&&x.instanceColor&&(at=x.instanceColor)),I===void 0||I.attribute!==at||at&&I.data!==at.data)return!0;H++}return r.attributesNum!==H||r.index!==F}function g(x,L,U,F){let z={},q=L.attributes,H=0,W=U.getAttributes();for(let V in W)if(W[V].location>=0){let I=q[V];I===void 0&&(V==="instanceMatrix"&&x.instanceMatrix&&(I=x.instanceMatrix),V==="instanceColor"&&x.instanceColor&&(I=x.instanceColor));let at={};at.attribute=I,I&&I.data&&(at.data=I.data),z[V]=at,H++}r.attributes=z,r.attributesNum=H,r.index=F}function _(){let x=r.newAttributes;for(let L=0,U=x.length;L<U;L++)x[L]=0}function m(x){p(x,0)}function p(x,L){let U=r.newAttributes,F=r.enabledAttributes,z=r.attributeDivisors;U[x]=1,F[x]===0&&(s.enableVertexAttribArray(x),F[x]=1),z[x]!==L&&(s.vertexAttribDivisor(x,L),z[x]=L)}function S(){let x=r.newAttributes,L=r.enabledAttributes;for(let U=0,F=L.length;U<F;U++)L[U]!==x[U]&&(s.disableVertexAttribArray(U),L[U]=0)}function y(x,L,U,F,z,q,H){H===!0?s.vertexAttribIPointer(x,L,U,z,q):s.vertexAttribPointer(x,L,U,F,z,q)}function v(x,L,U,F){_();let z=F.attributes,q=U.getAttributes(),H=L.defaultAttributeValues;for(let W in q){let V=q[W];if(V.location>=0){let st=z[W];if(st===void 0&&(W==="instanceMatrix"&&x.instanceMatrix&&(st=x.instanceMatrix),W==="instanceColor"&&x.instanceColor&&(st=x.instanceColor)),st!==void 0){let I=st.normalized,at=st.itemSize,Dt=t.get(st);if(Dt===void 0)continue;let Vt=Dt.buffer,Z=Dt.type,rt=Dt.bytesPerElement,St=Z===s.INT||Z===s.UNSIGNED_INT||st.gpuType===Bd;if(st.isInterleavedBufferAttribute){let ot=st.data,Rt=ot.stride,Bt=st.offset;if(ot.isInstancedInterleavedBuffer){for(let Wt=0;Wt<V.locationSize;Wt++)p(V.location+Wt,ot.meshPerAttribute);x.isInstancedMesh!==!0&&F._maxInstanceCount===void 0&&(F._maxInstanceCount=ot.meshPerAttribute*ot.count)}else for(let Wt=0;Wt<V.locationSize;Wt++)m(V.location+Wt);s.bindBuffer(s.ARRAY_BUFFER,Vt);for(let Wt=0;Wt<V.locationSize;Wt++)y(V.location+Wt,at/V.locationSize,Z,I,Rt*rt,(Bt+at/V.locationSize*Wt)*rt,St)}else{if(st.isInstancedBufferAttribute){for(let ot=0;ot<V.locationSize;ot++)p(V.location+ot,st.meshPerAttribute);x.isInstancedMesh!==!0&&F._maxInstanceCount===void 0&&(F._maxInstanceCount=st.meshPerAttribute*st.count)}else for(let ot=0;ot<V.locationSize;ot++)m(V.location+ot);s.bindBuffer(s.ARRAY_BUFFER,Vt);for(let ot=0;ot<V.locationSize;ot++)y(V.location+ot,at/V.locationSize,Z,I,at*rt,at/V.locationSize*ot*rt,St)}}else if(H!==void 0){let I=H[W];if(I!==void 0)switch(I.length){case 2:s.vertexAttrib2fv(V.location,I);break;case 3:s.vertexAttrib3fv(V.location,I);break;case 4:s.vertexAttrib4fv(V.location,I);break;default:s.vertexAttrib1fv(V.location,I)}}}}S()}function E(){R();for(let x in n){let L=n[x];for(let U in L){let F=L[U];for(let z in F)h(F[z].object),delete F[z];delete L[U]}delete n[x]}}function A(x){if(n[x.id]===void 0)return;let L=n[x.id];for(let U in L){let F=L[U];for(let z in F)h(F[z].object),delete F[z];delete L[U]}delete n[x.id]}function T(x){for(let L in n){let U=n[L];if(U[x.id]===void 0)continue;let F=U[x.id];for(let z in F)h(F[z].object),delete F[z];delete U[x.id]}}function R(){M(),o=!0,r!==i&&(r=i,c(r.object))}function M(){i.geometry=null,i.program=null,i.wireframe=!1}return{setup:a,reset:R,resetDefaultState:M,dispose:E,releaseStatesOfGeometry:A,releaseStatesOfProgram:T,initAttributes:_,enableAttribute:m,disableUnusedAttributes:S}}function _b(s,t,e){let n;function i(c){n=c}function r(c,h){s.drawArrays(n,c,h),e.update(h,n,1)}function o(c,h,u){u!==0&&(s.drawArraysInstanced(n,c,h,u),e.update(h,n,u))}function a(c,h,u){if(u===0)return;t.get("WEBGL_multi_draw").multiDrawArraysWEBGL(n,c,0,h,0,u);let d=0;for(let g=0;g<u;g++)d+=h[g];e.update(d,n,1)}function l(c,h,u,f){if(u===0)return;let d=t.get("WEBGL_multi_draw");if(d===null)for(let g=0;g<c.length;g++)o(c[g],h[g],f[g]);else{d.multiDrawArraysInstancedWEBGL(n,c,0,h,0,f,0,u);let g=0;for(let _=0;_<u;_++)g+=h[_]*f[_];e.update(g,n,1)}}this.setMode=i,this.render=r,this.renderInstances=o,this.renderMultiDraw=a,this.renderMultiDrawInstances=l}function vb(s,t,e,n){let i;function r(){if(i!==void 0)return i;if(t.has("EXT_texture_filter_anisotropic")===!0){let T=t.get("EXT_texture_filter_anisotropic");i=s.getParameter(T.MAX_TEXTURE_MAX_ANISOTROPY_EXT)}else i=0;return i}function o(T){return!(T!==bi&&n.convert(T)!==s.getParameter(s.IMPLEMENTATION_COLOR_READ_FORMAT))}function a(T){let R=T===ei&&(t.has("EXT_color_buffer_half_float")||t.has("EXT_color_buffer_float"));return!(T!==os&&n.convert(T)!==s.getParameter(s.IMPLEMENTATION_COLOR_READ_TYPE)&&T!==Bi&&!R)}function l(T){if(T==="highp"){if(s.getShaderPrecisionFormat(s.VERTEX_SHADER,s.HIGH_FLOAT).precision>0&&s.getShaderPrecisionFormat(s.FRAGMENT_SHADER,s.HIGH_FLOAT).precision>0)return"highp";T="mediump"}return T==="mediump"&&s.getShaderPrecisionFormat(s.VERTEX_SHADER,s.MEDIUM_FLOAT).precision>0&&s.getShaderPrecisionFormat(s.FRAGMENT_SHADER,s.MEDIUM_FLOAT).precision>0?"mediump":"lowp"}let c=e.precision!==void 0?e.precision:"highp",h=l(c);h!==c&&(console.warn("THREE.WebGLRenderer:",c,"not supported, using",h,"instead."),c=h);let u=e.logarithmicDepthBuffer===!0,f=e.reverseDepthBuffer===!0&&t.has("EXT_clip_control"),d=s.getParameter(s.MAX_TEXTURE_IMAGE_UNITS),g=s.getParameter(s.MAX_VERTEX_TEXTURE_IMAGE_UNITS),_=s.getParameter(s.MAX_TEXTURE_SIZE),m=s.getParameter(s.MAX_CUBE_MAP_TEXTURE_SIZE),p=s.getParameter(s.MAX_VERTEX_ATTRIBS),S=s.getParameter(s.MAX_VERTEX_UNIFORM_VECTORS),y=s.getParameter(s.MAX_VARYING_VECTORS),v=s.getParameter(s.MAX_FRAGMENT_UNIFORM_VECTORS),E=g>0,A=s.getParameter(s.MAX_SAMPLES);return{isWebGL2:!0,getMaxAnisotropy:r,getMaxPrecision:l,textureFormatReadable:o,textureTypeReadable:a,precision:c,logarithmicDepthBuffer:u,reverseDepthBuffer:f,maxTextures:d,maxVertexTextures:g,maxTextureSize:_,maxCubemapSize:m,maxAttributes:p,maxVertexUniforms:S,maxVaryings:y,maxFragmentUniforms:v,vertexTextures:E,maxSamples:A}}function xb(s){let t=this,e=null,n=0,i=!1,r=!1,o=new is,a=new oe,l={value:null,needsUpdate:!1};this.uniform=l,this.numPlanes=0,this.numIntersection=0,this.init=function(u,f){let d=u.length!==0||f||n!==0||i;return i=f,n=u.length,d},this.beginShadows=function(){r=!0,h(null)},this.endShadows=function(){r=!1},this.setGlobalState=function(u,f){e=h(u,f,0)},this.setState=function(u,f,d){let g=u.clippingPlanes,_=u.clipIntersection,m=u.clipShadows,p=s.get(u);if(!i||g===null||g.length===0||r&&!m)r?h(null):c();else{let S=r?0:n,y=S*4,v=p.clippingState||null;l.value=v,v=h(g,f,y,d);for(let E=0;E!==y;++E)v[E]=e[E];p.clippingState=v,this.numIntersection=_?this.numPlanes:0,this.numPlanes+=S}};function c(){l.value!==e&&(l.value=e,l.needsUpdate=n>0),t.numPlanes=n,t.numIntersection=0}function h(u,f,d,g){let _=u!==null?u.length:0,m=null;if(_!==0){if(m=l.value,g!==!0||m===null){let p=d+_*4,S=f.matrixWorldInverse;a.getNormalMatrix(S),(m===null||m.length<p)&&(m=new Float32Array(p));for(let y=0,v=d;y!==_;++y,v+=4)o.copy(u[y]).applyMatrix4(S,a),o.normal.toArray(m,v),m[v+3]=o.constant}l.value=m,l.needsUpdate=!0}return t.numPlanes=_,t.numIntersection=0,m}}function yb(s){let t=new WeakMap;function e(o,a){return a===gf?o.mapping=To:a===_f&&(o.mapping=Eo),o}function n(o){if(o&&o.isTexture){let a=o.mapping;if(a===gf||a===_f)if(t.has(o)){let l=t.get(o).texture;return e(l,o.mapping)}else{let l=o.image;if(l&&l.height>0){let c=new jf(l.height);return c.fromEquirectangularTexture(s,o),t.set(o,c),o.addEventListener("dispose",i),e(c.texture,o.mapping)}else return null}}return o}function i(o){let a=o.target;a.removeEventListener("dispose",i);let l=t.get(a);l!==void 0&&(t.delete(a),l.dispose())}function r(){t=new WeakMap}return{get:n,dispose:r}}var Po=class extends Pc{constructor(t=-1,e=1,n=1,i=-1,r=.1,o=2e3){super(),this.isOrthographicCamera=!0,this.type="OrthographicCamera",this.zoom=1,this.view=null,this.left=t,this.right=e,this.top=n,this.bottom=i,this.near=r,this.far=o,this.updateProjectionMatrix()}copy(t,e){return super.copy(t,e),this.left=t.left,this.right=t.right,this.top=t.top,this.bottom=t.bottom,this.near=t.near,this.far=t.far,this.zoom=t.zoom,this.view=t.view===null?null:Object.assign({},t.view),this}setViewOffset(t,e,n,i,r,o){this.view===null&&(this.view={enabled:!0,fullWidth:1,fullHeight:1,offsetX:0,offsetY:0,width:1,height:1}),this.view.enabled=!0,this.view.fullWidth=t,this.view.fullHeight=e,this.view.offsetX=n,this.view.offsetY=i,this.view.width=r,this.view.height=o,this.updateProjectionMatrix()}clearViewOffset(){this.view!==null&&(this.view.enabled=!1),this.updateProjectionMatrix()}updateProjectionMatrix(){let t=(this.right-this.left)/(2*this.zoom),e=(this.top-this.bottom)/(2*this.zoom),n=(this.right+this.left)/2,i=(this.top+this.bottom)/2,r=n-t,o=n+t,a=i+e,l=i-e;if(this.view!==null&&this.view.enabled){let c=(this.right-this.left)/this.view.fullWidth/this.zoom,h=(this.top-this.bottom)/this.view.fullHeight/this.zoom;r+=c*this.view.offsetX,o=r+c*this.view.width,a-=h*this.view.offsetY,l=a-h*this.view.height}this.projectionMatrix.makeOrthographic(r,o,a,l,this.near,this.far,this.coordinateSystem),this.projectionMatrixInverse.copy(this.projectionMatrix).invert()}toJSON(t){let e=super.toJSON(t);return e.object.zoom=this.zoom,e.object.left=this.left,e.object.right=this.right,e.object.top=this.top,e.object.bottom=this.bottom,e.object.near=this.near,e.object.far=this.far,this.view!==null&&(e.object.view=Object.assign({},this.view)),e}},vo=4,Zg=[.125,.215,.35,.446,.526,.582],vr=20,$u=new Po,$g=new se,Ju=null,Ku=0,Qu=0,ju=!1,mr=(1+Math.sqrt(5))/2,go=1/mr,Jg=[new B(-mr,go,0),new B(mr,go,0),new B(-go,0,mr),new B(go,0,mr),new B(0,mr,-go),new B(0,mr,go),new B(-1,1,-1),new B(1,1,-1),new B(-1,1,1),new B(1,1,1)],Io=class{constructor(t){this._renderer=t,this._pingPongRenderTarget=null,this._lodMax=0,this._cubeSize=0,this._lodPlanes=[],this._sizeLods=[],this._sigmas=[],this._blurMaterial=null,this._cubemapMaterial=null,this._equirectMaterial=null,this._compileMaterial(this._blurMaterial)}fromScene(t,e=0,n=.1,i=100){Ju=this._renderer.getRenderTarget(),Ku=this._renderer.getActiveCubeFace(),Qu=this._renderer.getActiveMipmapLevel(),ju=this._renderer.xr.enabled,this._renderer.xr.enabled=!1,this._setSize(256);let r=this._allocateTargets();return r.depthBuffer=!0,this._sceneToCubeUV(t,n,i,r),e>0&&this._blur(r,0,0,e),this._applyPMREM(r),this._cleanup(r),r}fromEquirectangular(t,e=null){return this._fromTexture(t,e)}fromCubemap(t,e=null){return this._fromTexture(t,e)}compileCubemapShader(){this._cubemapMaterial===null&&(this._cubemapMaterial=jg(),this._compileMaterial(this._cubemapMaterial))}compileEquirectangularShader(){this._equirectMaterial===null&&(this._equirectMaterial=Qg(),this._compileMaterial(this._equirectMaterial))}dispose(){this._dispose(),this._cubemapMaterial!==null&&this._cubemapMaterial.dispose(),this._equirectMaterial!==null&&this._equirectMaterial.dispose()}_setSize(t){this._lodMax=Math.floor(Math.log2(t)),this._cubeSize=Math.pow(2,this._lodMax)}_dispose(){this._blurMaterial!==null&&this._blurMaterial.dispose(),this._pingPongRenderTarget!==null&&this._pingPongRenderTarget.dispose();for(let t=0;t<this._lodPlanes.length;t++)this._lodPlanes[t].dispose()}_cleanup(t){this._renderer.setRenderTarget(Ju,Ku,Qu),this._renderer.xr.enabled=ju,t.scissorTest=!1,cc(t,0,0,t.width,t.height)}_fromTexture(t,e){t.mapping===To||t.mapping===Eo?this._setSize(t.image.length===0?16:t.image[0].width||t.image[0].image.width):this._setSize(t.image.width/4),Ju=this._renderer.getRenderTarget(),Ku=this._renderer.getActiveCubeFace(),Qu=this._renderer.getActiveMipmapLevel(),ju=this._renderer.xr.enabled,this._renderer.xr.enabled=!1;let n=e||this._allocateTargets();return this._textureToCubeUV(t,n),this._applyPMREM(n),this._cleanup(n),n}_allocateTargets(){let t=3*Math.max(this._cubeSize,112),e=4*this._cubeSize,n={magFilter:Fi,minFilter:Fi,generateMipmaps:!1,type:ei,format:bi,colorSpace:Oo,depthBuffer:!1},i=Kg(t,e,n);if(this._pingPongRenderTarget===null||this._pingPongRenderTarget.width!==t||this._pingPongRenderTarget.height!==e){this._pingPongRenderTarget!==null&&this._dispose(),this._pingPongRenderTarget=Kg(t,e,n);let{_lodMax:r}=this;({sizeLods:this._sizeLods,lodPlanes:this._lodPlanes,sigmas:this._sigmas}=Mb(r)),this._blurMaterial=Sb(r,t,e)}return i}_compileMaterial(t){let e=new ve(this._lodPlanes[0],t);this._renderer.compile(e,$u)}_sceneToCubeUV(t,e,n,i){let a=new bn(90,1,e,n),l=[1,-1,1,1,1,1],c=[1,1,1,-1,-1,-1],h=this._renderer,u=h.autoClear,f=h.toneMapping;h.getClearColor($g),h.toneMapping=Os,h.autoClear=!1;let d=new Ti({name:"PMREM.Background",side:wn,depthWrite:!1,depthTest:!1}),g=new ve(new wr,d),_=!1,m=t.background;m?m.isColor&&(d.color.copy(m),t.background=null,_=!0):(d.color.copy($g),_=!0);for(let p=0;p<6;p++){let S=p%3;S===0?(a.up.set(0,l[p],0),a.lookAt(c[p],0,0)):S===1?(a.up.set(0,0,l[p]),a.lookAt(0,c[p],0)):(a.up.set(0,l[p],0),a.lookAt(0,0,c[p]));let y=this._cubeSize;cc(i,S*y,p>2?y:0,y,y),h.setRenderTarget(i),_&&h.render(g,a),h.render(t,a)}g.geometry.dispose(),g.material.dispose(),h.toneMapping=f,h.autoClear=u,t.background=m}_textureToCubeUV(t,e){let n=this._renderer,i=t.mapping===To||t.mapping===Eo;i?(this._cubemapMaterial===null&&(this._cubemapMaterial=jg()),this._cubemapMaterial.uniforms.flipEnvMap.value=t.isRenderTargetTexture===!1?-1:1):this._equirectMaterial===null&&(this._equirectMaterial=Qg());let r=i?this._cubemapMaterial:this._equirectMaterial,o=new ve(this._lodPlanes[0],r),a=r.uniforms;a.envMap.value=t;let l=this._cubeSize;cc(e,0,0,3*l,2*l),n.setRenderTarget(e),n.render(o,$u)}_applyPMREM(t){let e=this._renderer,n=e.autoClear;e.autoClear=!1;let i=this._lodPlanes.length;for(let r=1;r<i;r++){let o=Math.sqrt(this._sigmas[r]*this._sigmas[r]-this._sigmas[r-1]*this._sigmas[r-1]),a=Jg[(i-r-1)%Jg.length];this._blur(t,r-1,r,o,a)}e.autoClear=n}_blur(t,e,n,i,r){let o=this._pingPongRenderTarget;this._halfBlur(t,o,e,n,i,"latitudinal",r),this._halfBlur(o,t,n,n,i,"longitudinal",r)}_halfBlur(t,e,n,i,r,o,a){let l=this._renderer,c=this._blurMaterial;o!=="latitudinal"&&o!=="longitudinal"&&console.error("blur direction must be either latitudinal or longitudinal!");let h=3,u=new ve(this._lodPlanes[i],c),f=c.uniforms,d=this._sizeLods[n]-1,g=isFinite(r)?Math.PI/(2*d):2*Math.PI/(2*vr-1),_=r/g,m=isFinite(r)?1+Math.floor(h*_):vr;m>vr&&console.warn(`sigmaRadians, ${r}, is too large and will clip, as it requested ${m} samples when the maximum is set to ${vr}`);let p=[],S=0;for(let T=0;T<vr;++T){let R=T/_,M=Math.exp(-R*R/2);p.push(M),T===0?S+=M:T<m&&(S+=2*M)}for(let T=0;T<p.length;T++)p[T]=p[T]/S;f.envMap.value=t.texture,f.samples.value=m,f.weights.value=p,f.latitudinal.value=o==="latitudinal",a&&(f.poleAxis.value=a);let{_lodMax:y}=this;f.dTheta.value=g,f.mipInt.value=y-n;let v=this._sizeLods[i],E=3*v*(i>y-vo?i-y+vo:0),A=4*(this._cubeSize-v);cc(e,E,A,3*v,2*v),l.setRenderTarget(e),l.render(u,$u)}};function Mb(s){let t=[],e=[],n=[],i=s,r=s-vo+1+Zg.length;for(let o=0;o<r;o++){let a=Math.pow(2,i);e.push(a);let l=1/a;o>s-vo?l=Zg[o-s+vo-1]:o===0&&(l=0),n.push(l);let c=1/(a-2),h=-c,u=1+c,f=[h,h,u,h,u,u,h,h,u,u,h,u],d=6,g=6,_=3,m=2,p=1,S=new Float32Array(_*g*d),y=new Float32Array(m*g*d),v=new Float32Array(p*g*d);for(let A=0;A<d;A++){let T=A%3*2/3-1,R=A>2?0:-1,M=[T,R,0,T+2/3,R,0,T+2/3,R+1,0,T,R,0,T+2/3,R+1,0,T,R+1,0];S.set(M,_*g*A),y.set(f,m*g*A);let x=[A,A,A,A,A,A];v.set(x,p*g*A)}let E=new Ei;E.setAttribute("position",new ti(S,_)),E.setAttribute("uv",new ti(y,m)),E.setAttribute("faceIndex",new ti(v,p)),t.push(E),i>vo&&i--}return{lodPlanes:t,sizeLods:e,sigmas:n}}function Kg(s,t,e){let n=new un(s,t,e);return n.texture.mapping=Zc,n.texture.name="PMREM.cubeUv",n.scissorTest=!0,n}function cc(s,t,e,n,i){s.viewport.set(t,e,n,i),s.scissor.set(t,e,n,i)}function Sb(s,t,e){let n=new Float32Array(vr),i=new B(0,1,0);return new je({name:"SphericalGaussianBlur",defines:{n:vr,CUBEUV_TEXEL_WIDTH:1/t,CUBEUV_TEXEL_HEIGHT:1/e,CUBEUV_MAX_MIP:`${s}.0`},uniforms:{envMap:{value:null},samples:{value:1},weights:{value:n},latitudinal:{value:!1},dTheta:{value:0},mipInt:{value:0},poleAxis:{value:i}},vertexShader:Yd(),fragmentShader:`

			precision mediump float;
			precision mediump int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;
			uniform int samples;
			uniform float weights[ n ];
			uniform bool latitudinal;
			uniform float dTheta;
			uniform float mipInt;
			uniform vec3 poleAxis;

			#define ENVMAP_TYPE_CUBE_UV
			#include <cube_uv_reflection_fragment>

			vec3 getSample( float theta, vec3 axis ) {

				float cosTheta = cos( theta );
				// Rodrigues' axis-angle rotation
				vec3 sampleDirection = vOutputDirection * cosTheta
					+ cross( axis, vOutputDirection ) * sin( theta )
					+ axis * dot( axis, vOutputDirection ) * ( 1.0 - cosTheta );

				return bilinearCubeUV( envMap, sampleDirection, mipInt );

			}

			void main() {

				vec3 axis = latitudinal ? poleAxis : cross( poleAxis, vOutputDirection );

				if ( all( equal( axis, vec3( 0.0 ) ) ) ) {

					axis = vec3( vOutputDirection.z, 0.0, - vOutputDirection.x );

				}

				axis = normalize( axis );

				gl_FragColor = vec4( 0.0, 0.0, 0.0, 1.0 );
				gl_FragColor.rgb += weights[ 0 ] * getSample( 0.0, axis );

				for ( int i = 1; i < n; i++ ) {

					if ( i >= samples ) {

						break;

					}

					float theta = dTheta * float( i );
					gl_FragColor.rgb += weights[ i ] * getSample( -1.0 * theta, axis );
					gl_FragColor.rgb += weights[ i ] * getSample( theta, axis );

				}

			}
		`,blending:ki,depthTest:!1,depthWrite:!1})}function Qg(){return new je({name:"EquirectangularToCubeUV",uniforms:{envMap:{value:null}},vertexShader:Yd(),fragmentShader:`

			precision mediump float;
			precision mediump int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;

			#include <common>

			void main() {

				vec3 outputDirection = normalize( vOutputDirection );
				vec2 uv = equirectUv( outputDirection );

				gl_FragColor = vec4( texture2D ( envMap, uv ).rgb, 1.0 );

			}
		`,blending:ki,depthTest:!1,depthWrite:!1})}function jg(){return new je({name:"CubemapToCubeUV",uniforms:{envMap:{value:null},flipEnvMap:{value:-1}},vertexShader:Yd(),fragmentShader:`

			precision mediump float;
			precision mediump int;

			uniform float flipEnvMap;

			varying vec3 vOutputDirection;

			uniform samplerCube envMap;

			void main() {

				gl_FragColor = textureCube( envMap, vec3( flipEnvMap * vOutputDirection.x, vOutputDirection.yz ) );

			}
		`,blending:ki,depthTest:!1,depthWrite:!1})}function Yd(){return`

		precision mediump float;
		precision mediump int;

		attribute float faceIndex;

		varying vec3 vOutputDirection;

		// RH coordinate system; PMREM face-indexing convention
		vec3 getDirection( vec2 uv, float face ) {

			uv = 2.0 * uv - 1.0;

			vec3 direction = vec3( uv, 1.0 );

			if ( face == 0.0 ) {

				direction = direction.zyx; // ( 1, v, u ) pos x

			} else if ( face == 1.0 ) {

				direction = direction.xzy;
				direction.xz *= -1.0; // ( -u, 1, -v ) pos y

			} else if ( face == 2.0 ) {

				direction.x *= -1.0; // ( -u, v, 1 ) pos z

			} else if ( face == 3.0 ) {

				direction = direction.zyx;
				direction.xz *= -1.0; // ( -1, v, -u ) neg x

			} else if ( face == 4.0 ) {

				direction = direction.xzy;
				direction.xy *= -1.0; // ( -u, -1, v ) neg y

			} else if ( face == 5.0 ) {

				direction.z *= -1.0; // ( u, v, -1 ) neg z

			}

			return direction;

		}

		void main() {

			vOutputDirection = getDirection( uv, faceIndex );
			gl_Position = vec4( position, 1.0 );

		}
	`}function bb(s){let t=new WeakMap,e=null;function n(a){if(a&&a.isTexture){let l=a.mapping,c=l===gf||l===_f,h=l===To||l===Eo;if(c||h){let u=t.get(a),f=u!==void 0?u.texture.pmremVersion:0;if(a.isRenderTargetTexture&&a.pmremVersion!==f)return e===null&&(e=new Io(s)),u=c?e.fromEquirectangular(a,u):e.fromCubemap(a,u),u.texture.pmremVersion=a.pmremVersion,t.set(a,u),u.texture;if(u!==void 0)return u.texture;{let d=a.image;return c&&d&&d.height>0||h&&d&&i(d)?(e===null&&(e=new Io(s)),u=c?e.fromEquirectangular(a):e.fromCubemap(a),u.texture.pmremVersion=a.pmremVersion,t.set(a,u),a.addEventListener("dispose",r),u.texture):null}}}return a}function i(a){let l=0,c=6;for(let h=0;h<c;h++)a[h]!==void 0&&l++;return l===c}function r(a){let l=a.target;l.removeEventListener("dispose",r);let c=t.get(l);c!==void 0&&(t.delete(l),c.dispose())}function o(){t=new WeakMap,e!==null&&(e.dispose(),e=null)}return{get:n,dispose:o}}function wb(s){let t={};function e(n){if(t[n]!==void 0)return t[n];let i;switch(n){case"WEBGL_depth_texture":i=s.getExtension("WEBGL_depth_texture")||s.getExtension("MOZ_WEBGL_depth_texture")||s.getExtension("WEBKIT_WEBGL_depth_texture");break;case"EXT_texture_filter_anisotropic":i=s.getExtension("EXT_texture_filter_anisotropic")||s.getExtension("MOZ_EXT_texture_filter_anisotropic")||s.getExtension("WEBKIT_EXT_texture_filter_anisotropic");break;case"WEBGL_compressed_texture_s3tc":i=s.getExtension("WEBGL_compressed_texture_s3tc")||s.getExtension("MOZ_WEBGL_compressed_texture_s3tc")||s.getExtension("WEBKIT_WEBGL_compressed_texture_s3tc");break;case"WEBGL_compressed_texture_pvrtc":i=s.getExtension("WEBGL_compressed_texture_pvrtc")||s.getExtension("WEBKIT_WEBGL_compressed_texture_pvrtc");break;default:i=s.getExtension(n)}return t[n]=i,i}return{has:function(n){return e(n)!==null},init:function(){e("EXT_color_buffer_float"),e("WEBGL_clip_cull_distance"),e("OES_texture_float_linear"),e("EXT_color_buffer_half_float"),e("WEBGL_multisampled_render_to_texture"),e("WEBGL_render_shared_exponent")},get:function(n){let i=e(n);return i===null&&Na("THREE.WebGLRenderer: "+n+" extension not supported."),i}}}function Tb(s,t,e,n){let i={},r=new WeakMap;function o(u){let f=u.target;f.index!==null&&t.remove(f.index);for(let g in f.attributes)t.remove(f.attributes[g]);for(let g in f.morphAttributes){let _=f.morphAttributes[g];for(let m=0,p=_.length;m<p;m++)t.remove(_[m])}f.removeEventListener("dispose",o),delete i[f.id];let d=r.get(f);d&&(t.remove(d),r.delete(f)),n.releaseStatesOfGeometry(f),f.isInstancedBufferGeometry===!0&&delete f._maxInstanceCount,e.memory.geometries--}function a(u,f){return i[f.id]===!0||(f.addEventListener("dispose",o),i[f.id]=!0,e.memory.geometries++),f}function l(u){let f=u.attributes;for(let g in f)t.update(f[g],s.ARRAY_BUFFER);let d=u.morphAttributes;for(let g in d){let _=d[g];for(let m=0,p=_.length;m<p;m++)t.update(_[m],s.ARRAY_BUFFER)}}function c(u){let f=[],d=u.index,g=u.attributes.position,_=0;if(d!==null){let S=d.array;_=d.version;for(let y=0,v=S.length;y<v;y+=3){let E=S[y+0],A=S[y+1],T=S[y+2];f.push(E,A,A,T,T,E)}}else if(g!==void 0){let S=g.array;_=g.version;for(let y=0,v=S.length/3-1;y<v;y+=3){let E=y+0,A=y+1,T=y+2;f.push(E,A,A,T,T,E)}}else return;let m=new(H_(f)?Rc:Cc)(f,1);m.version=_;let p=r.get(u);p&&t.remove(p),r.set(u,m)}function h(u){let f=r.get(u);if(f){let d=u.index;d!==null&&f.version<d.version&&c(u)}else c(u);return r.get(u)}return{get:a,update:l,getWireframeAttribute:h}}function Eb(s,t,e){let n;function i(f){n=f}let r,o;function a(f){r=f.type,o=f.bytesPerElement}function l(f,d){s.drawElements(n,d,r,f*o),e.update(d,n,1)}function c(f,d,g){g!==0&&(s.drawElementsInstanced(n,d,r,f*o,g),e.update(d,n,g))}function h(f,d,g){if(g===0)return;t.get("WEBGL_multi_draw").multiDrawElementsWEBGL(n,d,0,r,f,0,g);let m=0;for(let p=0;p<g;p++)m+=d[p];e.update(m,n,1)}function u(f,d,g,_){if(g===0)return;let m=t.get("WEBGL_multi_draw");if(m===null)for(let p=0;p<f.length;p++)c(f[p]/o,d[p],_[p]);else{m.multiDrawElementsInstancedWEBGL(n,d,0,r,f,0,_,0,g);let p=0;for(let S=0;S<g;S++)p+=d[S]*_[S];e.update(p,n,1)}}this.setMode=i,this.setIndex=a,this.render=l,this.renderInstances=c,this.renderMultiDraw=h,this.renderMultiDrawInstances=u}function Ab(s){let t={geometries:0,textures:0},e={frame:0,calls:0,triangles:0,points:0,lines:0};function n(r,o,a){switch(e.calls++,o){case s.TRIANGLES:e.triangles+=a*(r/3);break;case s.LINES:e.lines+=a*(r/2);break;case s.LINE_STRIP:e.lines+=a*(r-1);break;case s.LINE_LOOP:e.lines+=a*r;break;case s.POINTS:e.points+=a*r;break;default:console.error("THREE.WebGLInfo: Unknown draw mode:",o);break}}function i(){e.calls=0,e.triangles=0,e.points=0,e.lines=0}return{memory:t,render:e,programs:null,autoReset:!0,reset:i,update:n}}function Cb(s,t,e){let n=new WeakMap,i=new Ae;function r(o,a,l){let c=o.morphTargetInfluences,h=a.morphAttributes.position||a.morphAttributes.normal||a.morphAttributes.color,u=h!==void 0?h.length:0,f=n.get(a);if(f===void 0||f.count!==u){let M=function(){T.dispose(),n.delete(a),a.removeEventListener("dispose",M)};f!==void 0&&f.texture.dispose();let d=a.morphAttributes.position!==void 0,g=a.morphAttributes.normal!==void 0,_=a.morphAttributes.color!==void 0,m=a.morphAttributes.position||[],p=a.morphAttributes.normal||[],S=a.morphAttributes.color||[],y=0;d===!0&&(y=1),g===!0&&(y=2),_===!0&&(y=3);let v=a.attributes.position.count*y,E=1;v>t.maxTextureSize&&(E=Math.ceil(v/t.maxTextureSize),v=t.maxTextureSize);let A=new Float32Array(v*E*4*u),T=new Ec(A,v,E,u);T.type=Bi,T.needsUpdate=!0;let R=y*4;for(let x=0;x<u;x++){let L=m[x],U=p[x],F=S[x],z=v*E*4*x;for(let q=0;q<L.count;q++){let H=q*R;d===!0&&(i.fromBufferAttribute(L,q),A[z+H+0]=i.x,A[z+H+1]=i.y,A[z+H+2]=i.z,A[z+H+3]=0),g===!0&&(i.fromBufferAttribute(U,q),A[z+H+4]=i.x,A[z+H+5]=i.y,A[z+H+6]=i.z,A[z+H+7]=0),_===!0&&(i.fromBufferAttribute(F,q),A[z+H+8]=i.x,A[z+H+9]=i.y,A[z+H+10]=i.z,A[z+H+11]=F.itemSize===4?i.w:1)}}f={count:u,texture:T,size:new vt(v,E)},n.set(a,f),a.addEventListener("dispose",M)}if(o.isInstancedMesh===!0&&o.morphTexture!==null)l.getUniforms().setValue(s,"morphTexture",o.morphTexture,e);else{let d=0;for(let _=0;_<c.length;_++)d+=c[_];let g=a.morphTargetsRelative?1:1-d;l.getUniforms().setValue(s,"morphTargetBaseInfluence",g),l.getUniforms().setValue(s,"morphTargetInfluences",c)}l.getUniforms().setValue(s,"morphTargetsTexture",f.texture,e),l.getUniforms().setValue(s,"morphTargetsTextureSize",f.size)}return{update:r}}function Rb(s,t,e,n){let i=new WeakMap;function r(l){let c=n.render.frame,h=l.geometry,u=t.get(l,h);if(i.get(u)!==c&&(t.update(u),i.set(u,c)),l.isInstancedMesh&&(l.hasEventListener("dispose",a)===!1&&l.addEventListener("dispose",a),i.get(l)!==c&&(e.update(l.instanceMatrix,s.ARRAY_BUFFER),l.instanceColor!==null&&e.update(l.instanceColor,s.ARRAY_BUFFER),i.set(l,c))),l.isSkinnedMesh){let f=l.skeleton;i.get(f)!==c&&(f.update(),i.set(f,c))}return u}function o(){i=new WeakMap}function a(l){let c=l.target;c.removeEventListener("dispose",a),e.remove(c.instanceMatrix),c.instanceColor!==null&&e.remove(c.instanceColor)}return{update:r,dispose:o}}var Lc=class extends Vn{constructor(t,e,n,i,r,o,a,l,c,h=Mo){if(h!==Mo&&h!==Co)throw new Error("DepthTexture format must be either THREE.DepthFormat or THREE.DepthStencilFormat");n===void 0&&h===Mo&&(n=Mr),n===void 0&&h===Co&&(n=Ao),super(null,i,r,o,a,l,h,n,c),this.isDepthTexture=!0,this.image={width:t,height:e},this.magFilter=a!==void 0?a:jn,this.minFilter=l!==void 0?l:jn,this.flipY=!1,this.generateMipmaps=!1,this.compareFunction=null}copy(t){return super.copy(t),this.compareFunction=t.compareFunction,this}toJSON(t){let e=super.toJSON(t);return this.compareFunction!==null&&(e.compareFunction=this.compareFunction),e}},Y_=new Vn,t_=new Lc(1,1),q_=new Ec,Z_=new Jf,$_=new Ic,e_=[],n_=[],i_=new Float32Array(16),s_=new Float32Array(9),r_=new Float32Array(4);function Bo(s,t,e){let n=s[0];if(n<=0||n>0)return s;let i=t*e,r=e_[i];if(r===void 0&&(r=new Float32Array(i),e_[i]=r),t!==0){n.toArray(r,0);for(let o=1,a=0;o!==t;++o)a+=e,s[o].toArray(r,a)}return r}function tn(s,t){if(s.length!==t.length)return!1;for(let e=0,n=s.length;e<n;e++)if(s[e]!==t[e])return!1;return!0}function en(s,t){for(let e=0,n=t.length;e<n;e++)s[e]=t[e]}function Jc(s,t){let e=n_[t];e===void 0&&(e=new Int32Array(t),n_[t]=e);for(let n=0;n!==t;++n)e[n]=s.allocateTextureUnit();return e}function Pb(s,t){let e=this.cache;e[0]!==t&&(s.uniform1f(this.addr,t),e[0]=t)}function Ib(s,t){let e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y)&&(s.uniform2f(this.addr,t.x,t.y),e[0]=t.x,e[1]=t.y);else{if(tn(e,t))return;s.uniform2fv(this.addr,t),en(e,t)}}function Lb(s,t){let e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y||e[2]!==t.z)&&(s.uniform3f(this.addr,t.x,t.y,t.z),e[0]=t.x,e[1]=t.y,e[2]=t.z);else if(t.r!==void 0)(e[0]!==t.r||e[1]!==t.g||e[2]!==t.b)&&(s.uniform3f(this.addr,t.r,t.g,t.b),e[0]=t.r,e[1]=t.g,e[2]=t.b);else{if(tn(e,t))return;s.uniform3fv(this.addr,t),en(e,t)}}function Db(s,t){let e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y||e[2]!==t.z||e[3]!==t.w)&&(s.uniform4f(this.addr,t.x,t.y,t.z,t.w),e[0]=t.x,e[1]=t.y,e[2]=t.z,e[3]=t.w);else{if(tn(e,t))return;s.uniform4fv(this.addr,t),en(e,t)}}function Ub(s,t){let e=this.cache,n=t.elements;if(n===void 0){if(tn(e,t))return;s.uniformMatrix2fv(this.addr,!1,t),en(e,t)}else{if(tn(e,n))return;r_.set(n),s.uniformMatrix2fv(this.addr,!1,r_),en(e,n)}}function Nb(s,t){let e=this.cache,n=t.elements;if(n===void 0){if(tn(e,t))return;s.uniformMatrix3fv(this.addr,!1,t),en(e,t)}else{if(tn(e,n))return;s_.set(n),s.uniformMatrix3fv(this.addr,!1,s_),en(e,n)}}function Ob(s,t){let e=this.cache,n=t.elements;if(n===void 0){if(tn(e,t))return;s.uniformMatrix4fv(this.addr,!1,t),en(e,t)}else{if(tn(e,n))return;i_.set(n),s.uniformMatrix4fv(this.addr,!1,i_),en(e,n)}}function Fb(s,t){let e=this.cache;e[0]!==t&&(s.uniform1i(this.addr,t),e[0]=t)}function Bb(s,t){let e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y)&&(s.uniform2i(this.addr,t.x,t.y),e[0]=t.x,e[1]=t.y);else{if(tn(e,t))return;s.uniform2iv(this.addr,t),en(e,t)}}function kb(s,t){let e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y||e[2]!==t.z)&&(s.uniform3i(this.addr,t.x,t.y,t.z),e[0]=t.x,e[1]=t.y,e[2]=t.z);else{if(tn(e,t))return;s.uniform3iv(this.addr,t),en(e,t)}}function zb(s,t){let e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y||e[2]!==t.z||e[3]!==t.w)&&(s.uniform4i(this.addr,t.x,t.y,t.z,t.w),e[0]=t.x,e[1]=t.y,e[2]=t.z,e[3]=t.w);else{if(tn(e,t))return;s.uniform4iv(this.addr,t),en(e,t)}}function Vb(s,t){let e=this.cache;e[0]!==t&&(s.uniform1ui(this.addr,t),e[0]=t)}function Hb(s,t){let e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y)&&(s.uniform2ui(this.addr,t.x,t.y),e[0]=t.x,e[1]=t.y);else{if(tn(e,t))return;s.uniform2uiv(this.addr,t),en(e,t)}}function Gb(s,t){let e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y||e[2]!==t.z)&&(s.uniform3ui(this.addr,t.x,t.y,t.z),e[0]=t.x,e[1]=t.y,e[2]=t.z);else{if(tn(e,t))return;s.uniform3uiv(this.addr,t),en(e,t)}}function Wb(s,t){let e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y||e[2]!==t.z||e[3]!==t.w)&&(s.uniform4ui(this.addr,t.x,t.y,t.z,t.w),e[0]=t.x,e[1]=t.y,e[2]=t.z,e[3]=t.w);else{if(tn(e,t))return;s.uniform4uiv(this.addr,t),en(e,t)}}function Xb(s,t,e){let n=this.cache,i=e.allocateTextureUnit();n[0]!==i&&(s.uniform1i(this.addr,i),n[0]=i);let r;this.type===s.SAMPLER_2D_SHADOW?(t_.compareFunction=V_,r=t_):r=Y_,e.setTexture2D(t||r,i)}function Yb(s,t,e){let n=this.cache,i=e.allocateTextureUnit();n[0]!==i&&(s.uniform1i(this.addr,i),n[0]=i),e.setTexture3D(t||Z_,i)}function qb(s,t,e){let n=this.cache,i=e.allocateTextureUnit();n[0]!==i&&(s.uniform1i(this.addr,i),n[0]=i),e.setTextureCube(t||$_,i)}function Zb(s,t,e){let n=this.cache,i=e.allocateTextureUnit();n[0]!==i&&(s.uniform1i(this.addr,i),n[0]=i),e.setTexture2DArray(t||q_,i)}function $b(s){switch(s){case 5126:return Pb;case 35664:return Ib;case 35665:return Lb;case 35666:return Db;case 35674:return Ub;case 35675:return Nb;case 35676:return Ob;case 5124:case 35670:return Fb;case 35667:case 35671:return Bb;case 35668:case 35672:return kb;case 35669:case 35673:return zb;case 5125:return Vb;case 36294:return Hb;case 36295:return Gb;case 36296:return Wb;case 35678:case 36198:case 36298:case 36306:case 35682:return Xb;case 35679:case 36299:case 36307:return Yb;case 35680:case 36300:case 36308:case 36293:return qb;case 36289:case 36303:case 36311:case 36292:return Zb}}function Jb(s,t){s.uniform1fv(this.addr,t)}function Kb(s,t){let e=Bo(t,this.size,2);s.uniform2fv(this.addr,e)}function Qb(s,t){let e=Bo(t,this.size,3);s.uniform3fv(this.addr,e)}function jb(s,t){let e=Bo(t,this.size,4);s.uniform4fv(this.addr,e)}function t1(s,t){let e=Bo(t,this.size,4);s.uniformMatrix2fv(this.addr,!1,e)}function e1(s,t){let e=Bo(t,this.size,9);s.uniformMatrix3fv(this.addr,!1,e)}function n1(s,t){let e=Bo(t,this.size,16);s.uniformMatrix4fv(this.addr,!1,e)}function i1(s,t){s.uniform1iv(this.addr,t)}function s1(s,t){s.uniform2iv(this.addr,t)}function r1(s,t){s.uniform3iv(this.addr,t)}function o1(s,t){s.uniform4iv(this.addr,t)}function a1(s,t){s.uniform1uiv(this.addr,t)}function l1(s,t){s.uniform2uiv(this.addr,t)}function c1(s,t){s.uniform3uiv(this.addr,t)}function h1(s,t){s.uniform4uiv(this.addr,t)}function u1(s,t,e){let n=this.cache,i=t.length,r=Jc(e,i);tn(n,r)||(s.uniform1iv(this.addr,r),en(n,r));for(let o=0;o!==i;++o)e.setTexture2D(t[o]||Y_,r[o])}function f1(s,t,e){let n=this.cache,i=t.length,r=Jc(e,i);tn(n,r)||(s.uniform1iv(this.addr,r),en(n,r));for(let o=0;o!==i;++o)e.setTexture3D(t[o]||Z_,r[o])}function d1(s,t,e){let n=this.cache,i=t.length,r=Jc(e,i);tn(n,r)||(s.uniform1iv(this.addr,r),en(n,r));for(let o=0;o!==i;++o)e.setTextureCube(t[o]||$_,r[o])}function p1(s,t,e){let n=this.cache,i=t.length,r=Jc(e,i);tn(n,r)||(s.uniform1iv(this.addr,r),en(n,r));for(let o=0;o!==i;++o)e.setTexture2DArray(t[o]||q_,r[o])}function m1(s){switch(s){case 5126:return Jb;case 35664:return Kb;case 35665:return Qb;case 35666:return jb;case 35674:return t1;case 35675:return e1;case 35676:return n1;case 5124:case 35670:return i1;case 35667:case 35671:return s1;case 35668:case 35672:return r1;case 35669:case 35673:return o1;case 5125:return a1;case 36294:return l1;case 36295:return c1;case 36296:return h1;case 35678:case 36198:case 36298:case 36306:case 35682:return u1;case 35679:case 36299:case 36307:return f1;case 35680:case 36300:case 36308:case 36293:return d1;case 36289:case 36303:case 36311:case 36292:return p1}}var td=class{constructor(t,e,n){this.id=t,this.addr=n,this.cache=[],this.type=e.type,this.setValue=$b(e.type)}},ed=class{constructor(t,e,n){this.id=t,this.addr=n,this.cache=[],this.type=e.type,this.size=e.size,this.setValue=m1(e.type)}},nd=class{constructor(t){this.id=t,this.seq=[],this.map={}}setValue(t,e,n){let i=this.seq;for(let r=0,o=i.length;r!==o;++r){let a=i[r];a.setValue(t,e[a.id],n)}}},tf=/(\w+)(\])?(\[|\.)?/g;function o_(s,t){s.seq.push(t),s.map[t.id]=t}function g1(s,t,e){let n=s.name,i=n.length;for(tf.lastIndex=0;;){let r=tf.exec(n),o=tf.lastIndex,a=r[1],l=r[2]==="]",c=r[3];if(l&&(a=a|0),c===void 0||c==="["&&o+2===i){o_(e,c===void 0?new td(a,s,t):new ed(a,s,t));break}else{let u=e.map[a];u===void 0&&(u=new nd(a),o_(e,u)),e=u}}}var bo=class{constructor(t,e){this.seq=[],this.map={};let n=t.getProgramParameter(e,t.ACTIVE_UNIFORMS);for(let i=0;i<n;++i){let r=t.getActiveUniform(e,i),o=t.getUniformLocation(e,r.name);g1(r,o,this)}}setValue(t,e,n,i){let r=this.map[e];r!==void 0&&r.setValue(t,n,i)}setOptional(t,e,n){let i=e[n];i!==void 0&&this.setValue(t,n,i)}static upload(t,e,n,i){for(let r=0,o=e.length;r!==o;++r){let a=e[r],l=n[a.id];l.needsUpdate!==!1&&a.setValue(t,l.value,i)}}static seqWithValue(t,e){let n=[];for(let i=0,r=t.length;i!==r;++i){let o=t[i];o.id in e&&n.push(o)}return n}};function a_(s,t,e){let n=s.createShader(t);return s.shaderSource(n,e),s.compileShader(n),n}var _1=37297,v1=0;function x1(s,t){let e=s.split(`
`),n=[],i=Math.max(t-6,0),r=Math.min(t+6,e.length);for(let o=i;o<r;o++){let a=o+1;n.push(`${a===t?">":" "} ${a}: ${e[o]}`)}return n.join(`
`)}var l_=new oe;function y1(s){ge._getMatrix(l_,ge.workingColorSpace,s);let t=`mat3( ${l_.elements.map(e=>e.toFixed(4))} )`;switch(ge.getTransfer(s)){case $c:return[t,"LinearTransferOETF"];case we:return[t,"sRGBTransferOETF"];default:return console.warn("THREE.WebGLProgram: Unsupported color space: ",s),[t,"LinearTransferOETF"]}}function c_(s,t,e){let n=s.getShaderParameter(t,s.COMPILE_STATUS),i=s.getShaderInfoLog(t).trim();if(n&&i==="")return"";let r=/ERROR: 0:(\d+)/.exec(i);if(r){let o=parseInt(r[1]);return e.toUpperCase()+`

`+i+`

`+x1(s.getShaderSource(t),o)}else return i}function M1(s,t){let e=y1(t);return[`vec4 ${s}( vec4 value ) {`,`	return ${e[1]}( vec4( value.rgb * ${e[0]}, value.a ) );`,"}"].join(`
`)}function S1(s,t){let e;switch(t){case Dd:e="Linear";break;case Ud:e="Reinhard";break;case Nd:e="Cineon";break;case qa:e="ACESFilmic";break;case Od:e="AgX";break;case Fd:e="Neutral";break;case ty:e="Custom";break;default:console.warn("THREE.WebGLProgram: Unsupported toneMapping:",t),e="Linear"}return"vec3 "+s+"( vec3 color ) { return "+e+"ToneMapping( color ); }"}var hc=new B;function b1(){ge.getLuminanceCoefficients(hc);let s=hc.x.toFixed(4),t=hc.y.toFixed(4),e=hc.z.toFixed(4);return["float luminance( const in vec3 rgb ) {",`	const vec3 weights = vec3( ${s}, ${t}, ${e} );`,"	return dot( weights, rgb );","}"].join(`
`)}function w1(s){return[s.extensionClipCullDistance?"#extension GL_ANGLE_clip_cull_distance : require":"",s.extensionMultiDraw?"#extension GL_ANGLE_multi_draw : require":""].filter(Oa).join(`
`)}function T1(s){let t=[];for(let e in s){let n=s[e];n!==!1&&t.push("#define "+e+" "+n)}return t.join(`
`)}function E1(s,t){let e={},n=s.getProgramParameter(t,s.ACTIVE_ATTRIBUTES);for(let i=0;i<n;i++){let r=s.getActiveAttrib(t,i),o=r.name,a=1;r.type===s.FLOAT_MAT2&&(a=2),r.type===s.FLOAT_MAT3&&(a=3),r.type===s.FLOAT_MAT4&&(a=4),e[o]={type:r.type,location:s.getAttribLocation(t,o),locationSize:a}}return e}function Oa(s){return s!==""}function h_(s,t){let e=t.numSpotLightShadows+t.numSpotLightMaps-t.numSpotLightShadowsWithMaps;return s.replace(/NUM_DIR_LIGHTS/g,t.numDirLights).replace(/NUM_SPOT_LIGHTS/g,t.numSpotLights).replace(/NUM_SPOT_LIGHT_MAPS/g,t.numSpotLightMaps).replace(/NUM_SPOT_LIGHT_COORDS/g,e).replace(/NUM_RECT_AREA_LIGHTS/g,t.numRectAreaLights).replace(/NUM_POINT_LIGHTS/g,t.numPointLights).replace(/NUM_HEMI_LIGHTS/g,t.numHemiLights).replace(/NUM_DIR_LIGHT_SHADOWS/g,t.numDirLightShadows).replace(/NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS/g,t.numSpotLightShadowsWithMaps).replace(/NUM_SPOT_LIGHT_SHADOWS/g,t.numSpotLightShadows).replace(/NUM_POINT_LIGHT_SHADOWS/g,t.numPointLightShadows)}function u_(s,t){return s.replace(/NUM_CLIPPING_PLANES/g,t.numClippingPlanes).replace(/UNION_CLIPPING_PLANES/g,t.numClippingPlanes-t.numClipIntersection)}var A1=/^[ \t]*#include +<([\w\d./]+)>/gm;function id(s){return s.replace(A1,R1)}var C1=new Map;function R1(s,t){let e=ce[t];if(e===void 0){let n=C1.get(t);if(n!==void 0)e=ce[n],console.warn('THREE.WebGLRenderer: Shader chunk "%s" has been deprecated. Use "%s" instead.',t,n);else throw new Error("Can not resolve #include <"+t+">")}return id(e)}var P1=/#pragma unroll_loop_start\s+for\s*\(\s*int\s+i\s*=\s*(\d+)\s*;\s*i\s*<\s*(\d+)\s*;\s*i\s*\+\+\s*\)\s*{([\s\S]+?)}\s+#pragma unroll_loop_end/g;function f_(s){return s.replace(P1,I1)}function I1(s,t,e,n){let i="";for(let r=parseInt(t);r<parseInt(e);r++)i+=n.replace(/\[\s*i\s*\]/g,"[ "+r+" ]").replace(/UNROLLED_LOOP_INDEX/g,r);return i}function d_(s){let t=`precision ${s.precision} float;
	precision ${s.precision} int;
	precision ${s.precision} sampler2D;
	precision ${s.precision} samplerCube;
	precision ${s.precision} sampler3D;
	precision ${s.precision} sampler2DArray;
	precision ${s.precision} sampler2DShadow;
	precision ${s.precision} samplerCubeShadow;
	precision ${s.precision} sampler2DArrayShadow;
	precision ${s.precision} isampler2D;
	precision ${s.precision} isampler3D;
	precision ${s.precision} isamplerCube;
	precision ${s.precision} isampler2DArray;
	precision ${s.precision} usampler2D;
	precision ${s.precision} usampler3D;
	precision ${s.precision} usamplerCube;
	precision ${s.precision} usampler2DArray;
	`;return s.precision==="highp"?t+=`
#define HIGH_PRECISION`:s.precision==="mediump"?t+=`
#define MEDIUM_PRECISION`:s.precision==="lowp"&&(t+=`
#define LOW_PRECISION`),t}function L1(s){let t="SHADOWMAP_TYPE_BASIC";return s.shadowMapType===C_?t="SHADOWMAP_TYPE_PCF":s.shadowMapType===Dx?t="SHADOWMAP_TYPE_PCF_SOFT":s.shadowMapType===ns&&(t="SHADOWMAP_TYPE_VSM"),t}function D1(s){let t="ENVMAP_TYPE_CUBE";if(s.envMap)switch(s.envMapMode){case To:case Eo:t="ENVMAP_TYPE_CUBE";break;case Zc:t="ENVMAP_TYPE_CUBE_UV";break}return t}function U1(s){let t="ENVMAP_MODE_REFLECTION";if(s.envMap)switch(s.envMapMode){case Eo:t="ENVMAP_MODE_REFRACTION";break}return t}function N1(s){let t="ENVMAP_BLENDING_NONE";if(s.envMap)switch(s.combine){case R_:t="ENVMAP_BLENDING_MULTIPLY";break;case Qx:t="ENVMAP_BLENDING_MIX";break;case jx:t="ENVMAP_BLENDING_ADD";break}return t}function O1(s){let t=s.envMapCubeUVHeight;if(t===null)return null;let e=Math.log2(t)-2,n=1/t;return{texelWidth:1/(3*Math.max(Math.pow(2,e),112)),texelHeight:n,maxMip:e}}function F1(s,t,e,n){let i=s.getContext(),r=e.defines,o=e.vertexShader,a=e.fragmentShader,l=L1(e),c=D1(e),h=U1(e),u=N1(e),f=O1(e),d=w1(e),g=T1(r),_=i.createProgram(),m,p,S=e.glslVersion?"#version "+e.glslVersion+`
`:"";e.isRawShaderMaterial?(m=["#define SHADER_TYPE "+e.shaderType,"#define SHADER_NAME "+e.shaderName,g].filter(Oa).join(`
`),m.length>0&&(m+=`
`),p=["#define SHADER_TYPE "+e.shaderType,"#define SHADER_NAME "+e.shaderName,g].filter(Oa).join(`
`),p.length>0&&(p+=`
`)):(m=[d_(e),"#define SHADER_TYPE "+e.shaderType,"#define SHADER_NAME "+e.shaderName,g,e.extensionClipCullDistance?"#define USE_CLIP_DISTANCE":"",e.batching?"#define USE_BATCHING":"",e.batchingColor?"#define USE_BATCHING_COLOR":"",e.instancing?"#define USE_INSTANCING":"",e.instancingColor?"#define USE_INSTANCING_COLOR":"",e.instancingMorph?"#define USE_INSTANCING_MORPH":"",e.useFog&&e.fog?"#define USE_FOG":"",e.useFog&&e.fogExp2?"#define FOG_EXP2":"",e.map?"#define USE_MAP":"",e.envMap?"#define USE_ENVMAP":"",e.envMap?"#define "+h:"",e.lightMap?"#define USE_LIGHTMAP":"",e.aoMap?"#define USE_AOMAP":"",e.bumpMap?"#define USE_BUMPMAP":"",e.normalMap?"#define USE_NORMALMAP":"",e.normalMapObjectSpace?"#define USE_NORMALMAP_OBJECTSPACE":"",e.normalMapTangentSpace?"#define USE_NORMALMAP_TANGENTSPACE":"",e.displacementMap?"#define USE_DISPLACEMENTMAP":"",e.emissiveMap?"#define USE_EMISSIVEMAP":"",e.anisotropy?"#define USE_ANISOTROPY":"",e.anisotropyMap?"#define USE_ANISOTROPYMAP":"",e.clearcoatMap?"#define USE_CLEARCOATMAP":"",e.clearcoatRoughnessMap?"#define USE_CLEARCOAT_ROUGHNESSMAP":"",e.clearcoatNormalMap?"#define USE_CLEARCOAT_NORMALMAP":"",e.iridescenceMap?"#define USE_IRIDESCENCEMAP":"",e.iridescenceThicknessMap?"#define USE_IRIDESCENCE_THICKNESSMAP":"",e.specularMap?"#define USE_SPECULARMAP":"",e.specularColorMap?"#define USE_SPECULAR_COLORMAP":"",e.specularIntensityMap?"#define USE_SPECULAR_INTENSITYMAP":"",e.roughnessMap?"#define USE_ROUGHNESSMAP":"",e.metalnessMap?"#define USE_METALNESSMAP":"",e.alphaMap?"#define USE_ALPHAMAP":"",e.alphaHash?"#define USE_ALPHAHASH":"",e.transmission?"#define USE_TRANSMISSION":"",e.transmissionMap?"#define USE_TRANSMISSIONMAP":"",e.thicknessMap?"#define USE_THICKNESSMAP":"",e.sheenColorMap?"#define USE_SHEEN_COLORMAP":"",e.sheenRoughnessMap?"#define USE_SHEEN_ROUGHNESSMAP":"",e.mapUv?"#define MAP_UV "+e.mapUv:"",e.alphaMapUv?"#define ALPHAMAP_UV "+e.alphaMapUv:"",e.lightMapUv?"#define LIGHTMAP_UV "+e.lightMapUv:"",e.aoMapUv?"#define AOMAP_UV "+e.aoMapUv:"",e.emissiveMapUv?"#define EMISSIVEMAP_UV "+e.emissiveMapUv:"",e.bumpMapUv?"#define BUMPMAP_UV "+e.bumpMapUv:"",e.normalMapUv?"#define NORMALMAP_UV "+e.normalMapUv:"",e.displacementMapUv?"#define DISPLACEMENTMAP_UV "+e.displacementMapUv:"",e.metalnessMapUv?"#define METALNESSMAP_UV "+e.metalnessMapUv:"",e.roughnessMapUv?"#define ROUGHNESSMAP_UV "+e.roughnessMapUv:"",e.anisotropyMapUv?"#define ANISOTROPYMAP_UV "+e.anisotropyMapUv:"",e.clearcoatMapUv?"#define CLEARCOATMAP_UV "+e.clearcoatMapUv:"",e.clearcoatNormalMapUv?"#define CLEARCOAT_NORMALMAP_UV "+e.clearcoatNormalMapUv:"",e.clearcoatRoughnessMapUv?"#define CLEARCOAT_ROUGHNESSMAP_UV "+e.clearcoatRoughnessMapUv:"",e.iridescenceMapUv?"#define IRIDESCENCEMAP_UV "+e.iridescenceMapUv:"",e.iridescenceThicknessMapUv?"#define IRIDESCENCE_THICKNESSMAP_UV "+e.iridescenceThicknessMapUv:"",e.sheenColorMapUv?"#define SHEEN_COLORMAP_UV "+e.sheenColorMapUv:"",e.sheenRoughnessMapUv?"#define SHEEN_ROUGHNESSMAP_UV "+e.sheenRoughnessMapUv:"",e.specularMapUv?"#define SPECULARMAP_UV "+e.specularMapUv:"",e.specularColorMapUv?"#define SPECULAR_COLORMAP_UV "+e.specularColorMapUv:"",e.specularIntensityMapUv?"#define SPECULAR_INTENSITYMAP_UV "+e.specularIntensityMapUv:"",e.transmissionMapUv?"#define TRANSMISSIONMAP_UV "+e.transmissionMapUv:"",e.thicknessMapUv?"#define THICKNESSMAP_UV "+e.thicknessMapUv:"",e.vertexTangents&&e.flatShading===!1?"#define USE_TANGENT":"",e.vertexColors?"#define USE_COLOR":"",e.vertexAlphas?"#define USE_COLOR_ALPHA":"",e.vertexUv1s?"#define USE_UV1":"",e.vertexUv2s?"#define USE_UV2":"",e.vertexUv3s?"#define USE_UV3":"",e.pointsUvs?"#define USE_POINTS_UV":"",e.flatShading?"#define FLAT_SHADED":"",e.skinning?"#define USE_SKINNING":"",e.morphTargets?"#define USE_MORPHTARGETS":"",e.morphNormals&&e.flatShading===!1?"#define USE_MORPHNORMALS":"",e.morphColors?"#define USE_MORPHCOLORS":"",e.morphTargetsCount>0?"#define MORPHTARGETS_TEXTURE_STRIDE "+e.morphTextureStride:"",e.morphTargetsCount>0?"#define MORPHTARGETS_COUNT "+e.morphTargetsCount:"",e.doubleSided?"#define DOUBLE_SIDED":"",e.flipSided?"#define FLIP_SIDED":"",e.shadowMapEnabled?"#define USE_SHADOWMAP":"",e.shadowMapEnabled?"#define "+l:"",e.sizeAttenuation?"#define USE_SIZEATTENUATION":"",e.numLightProbes>0?"#define USE_LIGHT_PROBES":"",e.logarithmicDepthBuffer?"#define USE_LOGDEPTHBUF":"",e.reverseDepthBuffer?"#define USE_REVERSEDEPTHBUF":"","uniform mat4 modelMatrix;","uniform mat4 modelViewMatrix;","uniform mat4 projectionMatrix;","uniform mat4 viewMatrix;","uniform mat3 normalMatrix;","uniform vec3 cameraPosition;","uniform bool isOrthographic;","#ifdef USE_INSTANCING","	attribute mat4 instanceMatrix;","#endif","#ifdef USE_INSTANCING_COLOR","	attribute vec3 instanceColor;","#endif","#ifdef USE_INSTANCING_MORPH","	uniform sampler2D morphTexture;","#endif","attribute vec3 position;","attribute vec3 normal;","attribute vec2 uv;","#ifdef USE_UV1","	attribute vec2 uv1;","#endif","#ifdef USE_UV2","	attribute vec2 uv2;","#endif","#ifdef USE_UV3","	attribute vec2 uv3;","#endif","#ifdef USE_TANGENT","	attribute vec4 tangent;","#endif","#if defined( USE_COLOR_ALPHA )","	attribute vec4 color;","#elif defined( USE_COLOR )","	attribute vec3 color;","#endif","#ifdef USE_SKINNING","	attribute vec4 skinIndex;","	attribute vec4 skinWeight;","#endif",`
`].filter(Oa).join(`
`),p=[d_(e),"#define SHADER_TYPE "+e.shaderType,"#define SHADER_NAME "+e.shaderName,g,e.useFog&&e.fog?"#define USE_FOG":"",e.useFog&&e.fogExp2?"#define FOG_EXP2":"",e.alphaToCoverage?"#define ALPHA_TO_COVERAGE":"",e.map?"#define USE_MAP":"",e.matcap?"#define USE_MATCAP":"",e.envMap?"#define USE_ENVMAP":"",e.envMap?"#define "+c:"",e.envMap?"#define "+h:"",e.envMap?"#define "+u:"",f?"#define CUBEUV_TEXEL_WIDTH "+f.texelWidth:"",f?"#define CUBEUV_TEXEL_HEIGHT "+f.texelHeight:"",f?"#define CUBEUV_MAX_MIP "+f.maxMip+".0":"",e.lightMap?"#define USE_LIGHTMAP":"",e.aoMap?"#define USE_AOMAP":"",e.bumpMap?"#define USE_BUMPMAP":"",e.normalMap?"#define USE_NORMALMAP":"",e.normalMapObjectSpace?"#define USE_NORMALMAP_OBJECTSPACE":"",e.normalMapTangentSpace?"#define USE_NORMALMAP_TANGENTSPACE":"",e.emissiveMap?"#define USE_EMISSIVEMAP":"",e.anisotropy?"#define USE_ANISOTROPY":"",e.anisotropyMap?"#define USE_ANISOTROPYMAP":"",e.clearcoat?"#define USE_CLEARCOAT":"",e.clearcoatMap?"#define USE_CLEARCOATMAP":"",e.clearcoatRoughnessMap?"#define USE_CLEARCOAT_ROUGHNESSMAP":"",e.clearcoatNormalMap?"#define USE_CLEARCOAT_NORMALMAP":"",e.dispersion?"#define USE_DISPERSION":"",e.iridescence?"#define USE_IRIDESCENCE":"",e.iridescenceMap?"#define USE_IRIDESCENCEMAP":"",e.iridescenceThicknessMap?"#define USE_IRIDESCENCE_THICKNESSMAP":"",e.specularMap?"#define USE_SPECULARMAP":"",e.specularColorMap?"#define USE_SPECULAR_COLORMAP":"",e.specularIntensityMap?"#define USE_SPECULAR_INTENSITYMAP":"",e.roughnessMap?"#define USE_ROUGHNESSMAP":"",e.metalnessMap?"#define USE_METALNESSMAP":"",e.alphaMap?"#define USE_ALPHAMAP":"",e.alphaTest?"#define USE_ALPHATEST":"",e.alphaHash?"#define USE_ALPHAHASH":"",e.sheen?"#define USE_SHEEN":"",e.sheenColorMap?"#define USE_SHEEN_COLORMAP":"",e.sheenRoughnessMap?"#define USE_SHEEN_ROUGHNESSMAP":"",e.transmission?"#define USE_TRANSMISSION":"",e.transmissionMap?"#define USE_TRANSMISSIONMAP":"",e.thicknessMap?"#define USE_THICKNESSMAP":"",e.vertexTangents&&e.flatShading===!1?"#define USE_TANGENT":"",e.vertexColors||e.instancingColor||e.batchingColor?"#define USE_COLOR":"",e.vertexAlphas?"#define USE_COLOR_ALPHA":"",e.vertexUv1s?"#define USE_UV1":"",e.vertexUv2s?"#define USE_UV2":"",e.vertexUv3s?"#define USE_UV3":"",e.pointsUvs?"#define USE_POINTS_UV":"",e.gradientMap?"#define USE_GRADIENTMAP":"",e.flatShading?"#define FLAT_SHADED":"",e.doubleSided?"#define DOUBLE_SIDED":"",e.flipSided?"#define FLIP_SIDED":"",e.shadowMapEnabled?"#define USE_SHADOWMAP":"",e.shadowMapEnabled?"#define "+l:"",e.premultipliedAlpha?"#define PREMULTIPLIED_ALPHA":"",e.numLightProbes>0?"#define USE_LIGHT_PROBES":"",e.decodeVideoTexture?"#define DECODE_VIDEO_TEXTURE":"",e.decodeVideoTextureEmissive?"#define DECODE_VIDEO_TEXTURE_EMISSIVE":"",e.logarithmicDepthBuffer?"#define USE_LOGDEPTHBUF":"",e.reverseDepthBuffer?"#define USE_REVERSEDEPTHBUF":"","uniform mat4 viewMatrix;","uniform vec3 cameraPosition;","uniform bool isOrthographic;",e.toneMapping!==Os?"#define TONE_MAPPING":"",e.toneMapping!==Os?ce.tonemapping_pars_fragment:"",e.toneMapping!==Os?S1("toneMapping",e.toneMapping):"",e.dithering?"#define DITHERING":"",e.opaque?"#define OPAQUE":"",ce.colorspace_pars_fragment,M1("linearToOutputTexel",e.outputColorSpace),b1(),e.useDepthPacking?"#define DEPTH_PACKING "+e.depthPacking:"",`
`].filter(Oa).join(`
`)),o=id(o),o=h_(o,e),o=u_(o,e),a=id(a),a=h_(a,e),a=u_(a,e),o=f_(o),a=f_(a),e.isRawShaderMaterial!==!0&&(S=`#version 300 es
`,m=[d,"#define attribute in","#define varying out","#define texture2D texture"].join(`
`)+`
`+m,p=["#define varying in",e.glslVersion===Ag?"":"layout(location = 0) out highp vec4 pc_fragColor;",e.glslVersion===Ag?"":"#define gl_FragColor pc_fragColor","#define gl_FragDepthEXT gl_FragDepth","#define texture2D texture","#define textureCube texture","#define texture2DProj textureProj","#define texture2DLodEXT textureLod","#define texture2DProjLodEXT textureProjLod","#define textureCubeLodEXT textureLod","#define texture2DGradEXT textureGrad","#define texture2DProjGradEXT textureProjGrad","#define textureCubeGradEXT textureGrad"].join(`
`)+`
`+p);let y=S+m+o,v=S+p+a,E=a_(i,i.VERTEX_SHADER,y),A=a_(i,i.FRAGMENT_SHADER,v);i.attachShader(_,E),i.attachShader(_,A),e.index0AttributeName!==void 0?i.bindAttribLocation(_,0,e.index0AttributeName):e.morphTargets===!0&&i.bindAttribLocation(_,0,"position"),i.linkProgram(_);function T(L){if(s.debug.checkShaderErrors){let U=i.getProgramInfoLog(_).trim(),F=i.getShaderInfoLog(E).trim(),z=i.getShaderInfoLog(A).trim(),q=!0,H=!0;if(i.getProgramParameter(_,i.LINK_STATUS)===!1)if(q=!1,typeof s.debug.onShaderError=="function")s.debug.onShaderError(i,_,E,A);else{let W=c_(i,E,"vertex"),V=c_(i,A,"fragment");console.error("THREE.WebGLProgram: Shader Error "+i.getError()+" - VALIDATE_STATUS "+i.getProgramParameter(_,i.VALIDATE_STATUS)+`

Material Name: `+L.name+`
Material Type: `+L.type+`

Program Info Log: `+U+`
`+W+`
`+V)}else U!==""?console.warn("THREE.WebGLProgram: Program Info Log:",U):(F===""||z==="")&&(H=!1);H&&(L.diagnostics={runnable:q,programLog:U,vertexShader:{log:F,prefix:m},fragmentShader:{log:z,prefix:p}})}i.deleteShader(E),i.deleteShader(A),R=new bo(i,_),M=E1(i,_)}let R;this.getUniforms=function(){return R===void 0&&T(this),R};let M;this.getAttributes=function(){return M===void 0&&T(this),M};let x=e.rendererExtensionParallelShaderCompile===!1;return this.isReady=function(){return x===!1&&(x=i.getProgramParameter(_,_1)),x},this.destroy=function(){n.releaseStatesOfProgram(this),i.deleteProgram(_),this.program=void 0},this.type=e.shaderType,this.name=e.shaderName,this.id=v1++,this.cacheKey=t,this.usedTimes=1,this.program=_,this.vertexShader=E,this.fragmentShader=A,this}var B1=0,sd=class{constructor(){this.shaderCache=new Map,this.materialCache=new Map}update(t){let e=t.vertexShader,n=t.fragmentShader,i=this._getShaderStage(e),r=this._getShaderStage(n),o=this._getShaderCacheForMaterial(t);return o.has(i)===!1&&(o.add(i),i.usedTimes++),o.has(r)===!1&&(o.add(r),r.usedTimes++),this}remove(t){let e=this.materialCache.get(t);for(let n of e)n.usedTimes--,n.usedTimes===0&&this.shaderCache.delete(n.code);return this.materialCache.delete(t),this}getVertexShaderID(t){return this._getShaderStage(t.vertexShader).id}getFragmentShaderID(t){return this._getShaderStage(t.fragmentShader).id}dispose(){this.shaderCache.clear(),this.materialCache.clear()}_getShaderCacheForMaterial(t){let e=this.materialCache,n=e.get(t);return n===void 0&&(n=new Set,e.set(t,n)),n}_getShaderStage(t){let e=this.shaderCache,n=e.get(t);return n===void 0&&(n=new rd(t),e.set(t,n)),n}},rd=class{constructor(t){this.id=B1++,this.code=t,this.usedTimes=0}};function k1(s,t,e,n,i,r,o){let a=new Ac,l=new sd,c=new Set,h=[],u=i.logarithmicDepthBuffer,f=i.vertexTextures,d=i.precision,g={MeshDepthMaterial:"depth",MeshDistanceMaterial:"distanceRGBA",MeshNormalMaterial:"normal",MeshBasicMaterial:"basic",MeshLambertMaterial:"lambert",MeshPhongMaterial:"phong",MeshToonMaterial:"toon",MeshStandardMaterial:"physical",MeshPhysicalMaterial:"physical",MeshMatcapMaterial:"matcap",LineBasicMaterial:"basic",LineDashedMaterial:"dashed",PointsMaterial:"points",ShadowMaterial:"shadow",SpriteMaterial:"sprite"};function _(M){return c.add(M),M===0?"uv":`uv${M}`}function m(M,x,L,U,F){let z=U.fog,q=F.geometry,H=M.isMeshStandardMaterial?U.environment:null,W=(M.isMeshStandardMaterial?e:t).get(M.envMap||H),V=W&&W.mapping===Zc?W.image.height:null,st=g[M.type];M.precision!==null&&(d=i.getMaxPrecision(M.precision),d!==M.precision&&console.warn("THREE.WebGLProgram.getParameters:",M.precision,"not supported, using",d,"instead."));let I=q.morphAttributes.position||q.morphAttributes.normal||q.morphAttributes.color,at=I!==void 0?I.length:0,Dt=0;q.morphAttributes.position!==void 0&&(Dt=1),q.morphAttributes.normal!==void 0&&(Dt=2),q.morphAttributes.color!==void 0&&(Dt=3);let Vt,Z,rt,St;if(st){let J=Oi[st];Vt=J.vertexShader,Z=J.fragmentShader}else Vt=M.vertexShader,Z=M.fragmentShader,l.update(M),rt=l.getVertexShaderID(M),St=l.getFragmentShaderID(M);let ot=s.getRenderTarget(),Rt=s.state.buffers.depth.getReversed(),Bt=F.isInstancedMesh===!0,Wt=F.isBatchedMesh===!0,Xt=!!M.map,et=!!M.matcap,nt=!!W,P=!!M.aoMap,It=!!M.lightMap,lt=!!M.bumpMap,O=!!M.normalMap,dt=!!M.displacementMap,zt=!!M.emissiveMap,At=!!M.metalnessMap,C=!!M.roughnessMap,b=M.anisotropy>0,X=M.clearcoat>0,Q=M.dispersion>0,it=M.iridescence>0,j=M.sheen>0,xt=M.transmission>0,pt=b&&!!M.anisotropyMap,bt=X&&!!M.clearcoatMap,Kt=X&&!!M.clearcoatNormalMap,ut=X&&!!M.clearcoatRoughnessMap,gt=it&&!!M.iridescenceMap,qt=it&&!!M.iridescenceThicknessMap,Yt=j&&!!M.sheenColorMap,Lt=j&&!!M.sheenRoughnessMap,ee=!!M.specularMap,Jt=!!M.specularColorMap,Qt=!!M.specularIntensityMap,D=xt&&!!M.transmissionMap,yt=xt&&!!M.thicknessMap,$=!!M.gradientMap,tt=!!M.alphaMap,Mt=M.alphaTest>0,wt=!!M.alphaHash,K=!!M.extensions,ft=Os;M.toneMapped&&(ot===null||ot.isXRRenderTarget===!0)&&(ft=s.toneMapping);let Ut={shaderID:st,shaderType:M.type,shaderName:M.name,vertexShader:Vt,fragmentShader:Z,defines:M.defines,customVertexShaderID:rt,customFragmentShaderID:St,isRawShaderMaterial:M.isRawShaderMaterial===!0,glslVersion:M.glslVersion,precision:d,batching:Wt,batchingColor:Wt&&F._colorsTexture!==null,instancing:Bt,instancingColor:Bt&&F.instanceColor!==null,instancingMorph:Bt&&F.morphTexture!==null,supportsVertexTextures:f,outputColorSpace:ot===null?s.outputColorSpace:ot.isXRRenderTarget===!0?ot.texture.colorSpace:Oo,alphaToCoverage:!!M.alphaToCoverage,map:Xt,matcap:et,envMap:nt,envMapMode:nt&&W.mapping,envMapCubeUVHeight:V,aoMap:P,lightMap:It,bumpMap:lt,normalMap:O,displacementMap:f&&dt,emissiveMap:zt,normalMapObjectSpace:O&&M.normalMapType===sy,normalMapTangentSpace:O&&M.normalMapType===z_,metalnessMap:At,roughnessMap:C,anisotropy:b,anisotropyMap:pt,clearcoat:X,clearcoatMap:bt,clearcoatNormalMap:Kt,clearcoatRoughnessMap:ut,dispersion:Q,iridescence:it,iridescenceMap:gt,iridescenceThicknessMap:qt,sheen:j,sheenColorMap:Yt,sheenRoughnessMap:Lt,specularMap:ee,specularColorMap:Jt,specularIntensityMap:Qt,transmission:xt,transmissionMap:D,thicknessMap:yt,gradientMap:$,opaque:M.transparent===!1&&M.blending===yo&&M.alphaToCoverage===!1,alphaMap:tt,alphaTest:Mt,alphaHash:wt,combine:M.combine,mapUv:Xt&&_(M.map.channel),aoMapUv:P&&_(M.aoMap.channel),lightMapUv:It&&_(M.lightMap.channel),bumpMapUv:lt&&_(M.bumpMap.channel),normalMapUv:O&&_(M.normalMap.channel),displacementMapUv:dt&&_(M.displacementMap.channel),emissiveMapUv:zt&&_(M.emissiveMap.channel),metalnessMapUv:At&&_(M.metalnessMap.channel),roughnessMapUv:C&&_(M.roughnessMap.channel),anisotropyMapUv:pt&&_(M.anisotropyMap.channel),clearcoatMapUv:bt&&_(M.clearcoatMap.channel),clearcoatNormalMapUv:Kt&&_(M.clearcoatNormalMap.channel),clearcoatRoughnessMapUv:ut&&_(M.clearcoatRoughnessMap.channel),iridescenceMapUv:gt&&_(M.iridescenceMap.channel),iridescenceThicknessMapUv:qt&&_(M.iridescenceThicknessMap.channel),sheenColorMapUv:Yt&&_(M.sheenColorMap.channel),sheenRoughnessMapUv:Lt&&_(M.sheenRoughnessMap.channel),specularMapUv:ee&&_(M.specularMap.channel),specularColorMapUv:Jt&&_(M.specularColorMap.channel),specularIntensityMapUv:Qt&&_(M.specularIntensityMap.channel),transmissionMapUv:D&&_(M.transmissionMap.channel),thicknessMapUv:yt&&_(M.thicknessMap.channel),alphaMapUv:tt&&_(M.alphaMap.channel),vertexTangents:!!q.attributes.tangent&&(O||b),vertexColors:M.vertexColors,vertexAlphas:M.vertexColors===!0&&!!q.attributes.color&&q.attributes.color.itemSize===4,pointsUvs:F.isPoints===!0&&!!q.attributes.uv&&(Xt||tt),fog:!!z,useFog:M.fog===!0,fogExp2:!!z&&z.isFogExp2,flatShading:M.flatShading===!0,sizeAttenuation:M.sizeAttenuation===!0,logarithmicDepthBuffer:u,reverseDepthBuffer:Rt,skinning:F.isSkinnedMesh===!0,morphTargets:q.morphAttributes.position!==void 0,morphNormals:q.morphAttributes.normal!==void 0,morphColors:q.morphAttributes.color!==void 0,morphTargetsCount:at,morphTextureStride:Dt,numDirLights:x.directional.length,numPointLights:x.point.length,numSpotLights:x.spot.length,numSpotLightMaps:x.spotLightMap.length,numRectAreaLights:x.rectArea.length,numHemiLights:x.hemi.length,numDirLightShadows:x.directionalShadowMap.length,numPointLightShadows:x.pointShadowMap.length,numSpotLightShadows:x.spotShadowMap.length,numSpotLightShadowsWithMaps:x.numSpotLightShadowsWithMaps,numLightProbes:x.numLightProbes,numClippingPlanes:o.numPlanes,numClipIntersection:o.numIntersection,dithering:M.dithering,shadowMapEnabled:s.shadowMap.enabled&&L.length>0,shadowMapType:s.shadowMap.type,toneMapping:ft,decodeVideoTexture:Xt&&M.map.isVideoTexture===!0&&ge.getTransfer(M.map.colorSpace)===we,decodeVideoTextureEmissive:zt&&M.emissiveMap.isVideoTexture===!0&&ge.getTransfer(M.emissiveMap.colorSpace)===we,premultipliedAlpha:M.premultipliedAlpha,doubleSided:M.side===pi,flipSided:M.side===wn,useDepthPacking:M.depthPacking>=0,depthPacking:M.depthPacking||0,index0AttributeName:M.index0AttributeName,extensionClipCullDistance:K&&M.extensions.clipCullDistance===!0&&n.has("WEBGL_clip_cull_distance"),extensionMultiDraw:(K&&M.extensions.multiDraw===!0||Wt)&&n.has("WEBGL_multi_draw"),rendererExtensionParallelShaderCompile:n.has("KHR_parallel_shader_compile"),customProgramCacheKey:M.customProgramCacheKey()};return Ut.vertexUv1s=c.has(1),Ut.vertexUv2s=c.has(2),Ut.vertexUv3s=c.has(3),c.clear(),Ut}function p(M){let x=[];if(M.shaderID?x.push(M.shaderID):(x.push(M.customVertexShaderID),x.push(M.customFragmentShaderID)),M.defines!==void 0)for(let L in M.defines)x.push(L),x.push(M.defines[L]);return M.isRawShaderMaterial===!1&&(S(x,M),y(x,M),x.push(s.outputColorSpace)),x.push(M.customProgramCacheKey),x.join()}function S(M,x){M.push(x.precision),M.push(x.outputColorSpace),M.push(x.envMapMode),M.push(x.envMapCubeUVHeight),M.push(x.mapUv),M.push(x.alphaMapUv),M.push(x.lightMapUv),M.push(x.aoMapUv),M.push(x.bumpMapUv),M.push(x.normalMapUv),M.push(x.displacementMapUv),M.push(x.emissiveMapUv),M.push(x.metalnessMapUv),M.push(x.roughnessMapUv),M.push(x.anisotropyMapUv),M.push(x.clearcoatMapUv),M.push(x.clearcoatNormalMapUv),M.push(x.clearcoatRoughnessMapUv),M.push(x.iridescenceMapUv),M.push(x.iridescenceThicknessMapUv),M.push(x.sheenColorMapUv),M.push(x.sheenRoughnessMapUv),M.push(x.specularMapUv),M.push(x.specularColorMapUv),M.push(x.specularIntensityMapUv),M.push(x.transmissionMapUv),M.push(x.thicknessMapUv),M.push(x.combine),M.push(x.fogExp2),M.push(x.sizeAttenuation),M.push(x.morphTargetsCount),M.push(x.morphAttributeCount),M.push(x.numDirLights),M.push(x.numPointLights),M.push(x.numSpotLights),M.push(x.numSpotLightMaps),M.push(x.numHemiLights),M.push(x.numRectAreaLights),M.push(x.numDirLightShadows),M.push(x.numPointLightShadows),M.push(x.numSpotLightShadows),M.push(x.numSpotLightShadowsWithMaps),M.push(x.numLightProbes),M.push(x.shadowMapType),M.push(x.toneMapping),M.push(x.numClippingPlanes),M.push(x.numClipIntersection),M.push(x.depthPacking)}function y(M,x){a.disableAll(),x.supportsVertexTextures&&a.enable(0),x.instancing&&a.enable(1),x.instancingColor&&a.enable(2),x.instancingMorph&&a.enable(3),x.matcap&&a.enable(4),x.envMap&&a.enable(5),x.normalMapObjectSpace&&a.enable(6),x.normalMapTangentSpace&&a.enable(7),x.clearcoat&&a.enable(8),x.iridescence&&a.enable(9),x.alphaTest&&a.enable(10),x.vertexColors&&a.enable(11),x.vertexAlphas&&a.enable(12),x.vertexUv1s&&a.enable(13),x.vertexUv2s&&a.enable(14),x.vertexUv3s&&a.enable(15),x.vertexTangents&&a.enable(16),x.anisotropy&&a.enable(17),x.alphaHash&&a.enable(18),x.batching&&a.enable(19),x.dispersion&&a.enable(20),x.batchingColor&&a.enable(21),M.push(a.mask),a.disableAll(),x.fog&&a.enable(0),x.useFog&&a.enable(1),x.flatShading&&a.enable(2),x.logarithmicDepthBuffer&&a.enable(3),x.reverseDepthBuffer&&a.enable(4),x.skinning&&a.enable(5),x.morphTargets&&a.enable(6),x.morphNormals&&a.enable(7),x.morphColors&&a.enable(8),x.premultipliedAlpha&&a.enable(9),x.shadowMapEnabled&&a.enable(10),x.doubleSided&&a.enable(11),x.flipSided&&a.enable(12),x.useDepthPacking&&a.enable(13),x.dithering&&a.enable(14),x.transmission&&a.enable(15),x.sheen&&a.enable(16),x.opaque&&a.enable(17),x.pointsUvs&&a.enable(18),x.decodeVideoTexture&&a.enable(19),x.decodeVideoTextureEmissive&&a.enable(20),x.alphaToCoverage&&a.enable(21),M.push(a.mask)}function v(M){let x=g[M.type],L;if(x){let U=Oi[x];L=zs.clone(U.uniforms)}else L=M.uniforms;return L}function E(M,x){let L;for(let U=0,F=h.length;U<F;U++){let z=h[U];if(z.cacheKey===x){L=z,++L.usedTimes;break}}return L===void 0&&(L=new F1(s,x,M,r),h.push(L)),L}function A(M){if(--M.usedTimes===0){let x=h.indexOf(M);h[x]=h[h.length-1],h.pop(),M.destroy()}}function T(M){l.remove(M)}function R(){l.dispose()}return{getParameters:m,getProgramCacheKey:p,getUniforms:v,acquireProgram:E,releaseProgram:A,releaseShaderCache:T,programs:h,dispose:R}}function z1(){let s=new WeakMap;function t(o){return s.has(o)}function e(o){let a=s.get(o);return a===void 0&&(a={},s.set(o,a)),a}function n(o){s.delete(o)}function i(o,a,l){s.get(o)[a]=l}function r(){s=new WeakMap}return{has:t,get:e,remove:n,update:i,dispose:r}}function V1(s,t){return s.groupOrder!==t.groupOrder?s.groupOrder-t.groupOrder:s.renderOrder!==t.renderOrder?s.renderOrder-t.renderOrder:s.material.id!==t.material.id?s.material.id-t.material.id:s.z!==t.z?s.z-t.z:s.id-t.id}function p_(s,t){return s.groupOrder!==t.groupOrder?s.groupOrder-t.groupOrder:s.renderOrder!==t.renderOrder?s.renderOrder-t.renderOrder:s.z!==t.z?t.z-s.z:s.id-t.id}function m_(){let s=[],t=0,e=[],n=[],i=[];function r(){t=0,e.length=0,n.length=0,i.length=0}function o(u,f,d,g,_,m){let p=s[t];return p===void 0?(p={id:u.id,object:u,geometry:f,material:d,groupOrder:g,renderOrder:u.renderOrder,z:_,group:m},s[t]=p):(p.id=u.id,p.object=u,p.geometry=f,p.material=d,p.groupOrder=g,p.renderOrder=u.renderOrder,p.z=_,p.group=m),t++,p}function a(u,f,d,g,_,m){let p=o(u,f,d,g,_,m);d.transmission>0?n.push(p):d.transparent===!0?i.push(p):e.push(p)}function l(u,f,d,g,_,m){let p=o(u,f,d,g,_,m);d.transmission>0?n.unshift(p):d.transparent===!0?i.unshift(p):e.unshift(p)}function c(u,f){e.length>1&&e.sort(u||V1),n.length>1&&n.sort(f||p_),i.length>1&&i.sort(f||p_)}function h(){for(let u=t,f=s.length;u<f;u++){let d=s[u];if(d.id===null)break;d.id=null,d.object=null,d.geometry=null,d.material=null,d.group=null}}return{opaque:e,transmissive:n,transparent:i,init:r,push:a,unshift:l,finish:h,sort:c}}function H1(){let s=new WeakMap;function t(n,i){let r=s.get(n),o;return r===void 0?(o=new m_,s.set(n,[o])):i>=r.length?(o=new m_,r.push(o)):o=r[i],o}function e(){s=new WeakMap}return{get:t,dispose:e}}function G1(){let s={};return{get:function(t){if(s[t.id]!==void 0)return s[t.id];let e;switch(t.type){case"DirectionalLight":e={direction:new B,color:new se};break;case"SpotLight":e={position:new B,direction:new B,color:new se,distance:0,coneCos:0,penumbraCos:0,decay:0};break;case"PointLight":e={position:new B,color:new se,distance:0,decay:0};break;case"HemisphereLight":e={direction:new B,skyColor:new se,groundColor:new se};break;case"RectAreaLight":e={color:new se,position:new B,halfWidth:new B,halfHeight:new B};break}return s[t.id]=e,e}}}function W1(){let s={};return{get:function(t){if(s[t.id]!==void 0)return s[t.id];let e;switch(t.type){case"DirectionalLight":e={shadowIntensity:1,shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new vt};break;case"SpotLight":e={shadowIntensity:1,shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new vt};break;case"PointLight":e={shadowIntensity:1,shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new vt,shadowCameraNear:1,shadowCameraFar:1e3};break}return s[t.id]=e,e}}}var X1=0;function Y1(s,t){return(t.castShadow?2:0)-(s.castShadow?2:0)+(t.map?1:0)-(s.map?1:0)}function q1(s){let t=new G1,e=W1(),n={version:0,hash:{directionalLength:-1,pointLength:-1,spotLength:-1,rectAreaLength:-1,hemiLength:-1,numDirectionalShadows:-1,numPointShadows:-1,numSpotShadows:-1,numSpotMaps:-1,numLightProbes:-1},ambient:[0,0,0],probe:[],directional:[],directionalShadow:[],directionalShadowMap:[],directionalShadowMatrix:[],spot:[],spotLightMap:[],spotShadow:[],spotShadowMap:[],spotLightMatrix:[],rectArea:[],rectAreaLTC1:null,rectAreaLTC2:null,point:[],pointShadow:[],pointShadowMap:[],pointShadowMatrix:[],hemi:[],numSpotLightShadowsWithMaps:0,numLightProbes:0};for(let c=0;c<9;c++)n.probe.push(new B);let i=new B,r=new Ce,o=new Ce;function a(c){let h=0,u=0,f=0;for(let M=0;M<9;M++)n.probe[M].set(0,0,0);let d=0,g=0,_=0,m=0,p=0,S=0,y=0,v=0,E=0,A=0,T=0;c.sort(Y1);for(let M=0,x=c.length;M<x;M++){let L=c[M],U=L.color,F=L.intensity,z=L.distance,q=L.shadow&&L.shadow.map?L.shadow.map.texture:null;if(L.isAmbientLight)h+=U.r*F,u+=U.g*F,f+=U.b*F;else if(L.isLightProbe){for(let H=0;H<9;H++)n.probe[H].addScaledVector(L.sh.coefficients[H],F);T++}else if(L.isDirectionalLight){let H=t.get(L);if(H.color.copy(L.color).multiplyScalar(L.intensity),L.castShadow){let W=L.shadow,V=e.get(L);V.shadowIntensity=W.intensity,V.shadowBias=W.bias,V.shadowNormalBias=W.normalBias,V.shadowRadius=W.radius,V.shadowMapSize=W.mapSize,n.directionalShadow[d]=V,n.directionalShadowMap[d]=q,n.directionalShadowMatrix[d]=L.shadow.matrix,S++}n.directional[d]=H,d++}else if(L.isSpotLight){let H=t.get(L);H.position.setFromMatrixPosition(L.matrixWorld),H.color.copy(U).multiplyScalar(F),H.distance=z,H.coneCos=Math.cos(L.angle),H.penumbraCos=Math.cos(L.angle*(1-L.penumbra)),H.decay=L.decay,n.spot[_]=H;let W=L.shadow;if(L.map&&(n.spotLightMap[E]=L.map,E++,W.updateMatrices(L),L.castShadow&&A++),n.spotLightMatrix[_]=W.matrix,L.castShadow){let V=e.get(L);V.shadowIntensity=W.intensity,V.shadowBias=W.bias,V.shadowNormalBias=W.normalBias,V.shadowRadius=W.radius,V.shadowMapSize=W.mapSize,n.spotShadow[_]=V,n.spotShadowMap[_]=q,v++}_++}else if(L.isRectAreaLight){let H=t.get(L);H.color.copy(U).multiplyScalar(F),H.halfWidth.set(L.width*.5,0,0),H.halfHeight.set(0,L.height*.5,0),n.rectArea[m]=H,m++}else if(L.isPointLight){let H=t.get(L);if(H.color.copy(L.color).multiplyScalar(L.intensity),H.distance=L.distance,H.decay=L.decay,L.castShadow){let W=L.shadow,V=e.get(L);V.shadowIntensity=W.intensity,V.shadowBias=W.bias,V.shadowNormalBias=W.normalBias,V.shadowRadius=W.radius,V.shadowMapSize=W.mapSize,V.shadowCameraNear=W.camera.near,V.shadowCameraFar=W.camera.far,n.pointShadow[g]=V,n.pointShadowMap[g]=q,n.pointShadowMatrix[g]=L.shadow.matrix,y++}n.point[g]=H,g++}else if(L.isHemisphereLight){let H=t.get(L);H.skyColor.copy(L.color).multiplyScalar(F),H.groundColor.copy(L.groundColor).multiplyScalar(F),n.hemi[p]=H,p++}}m>0&&(s.has("OES_texture_float_linear")===!0?(n.rectAreaLTC1=Pt.LTC_FLOAT_1,n.rectAreaLTC2=Pt.LTC_FLOAT_2):(n.rectAreaLTC1=Pt.LTC_HALF_1,n.rectAreaLTC2=Pt.LTC_HALF_2)),n.ambient[0]=h,n.ambient[1]=u,n.ambient[2]=f;let R=n.hash;(R.directionalLength!==d||R.pointLength!==g||R.spotLength!==_||R.rectAreaLength!==m||R.hemiLength!==p||R.numDirectionalShadows!==S||R.numPointShadows!==y||R.numSpotShadows!==v||R.numSpotMaps!==E||R.numLightProbes!==T)&&(n.directional.length=d,n.spot.length=_,n.rectArea.length=m,n.point.length=g,n.hemi.length=p,n.directionalShadow.length=S,n.directionalShadowMap.length=S,n.pointShadow.length=y,n.pointShadowMap.length=y,n.spotShadow.length=v,n.spotShadowMap.length=v,n.directionalShadowMatrix.length=S,n.pointShadowMatrix.length=y,n.spotLightMatrix.length=v+E-A,n.spotLightMap.length=E,n.numSpotLightShadowsWithMaps=A,n.numLightProbes=T,R.directionalLength=d,R.pointLength=g,R.spotLength=_,R.rectAreaLength=m,R.hemiLength=p,R.numDirectionalShadows=S,R.numPointShadows=y,R.numSpotShadows=v,R.numSpotMaps=E,R.numLightProbes=T,n.version=X1++)}function l(c,h){let u=0,f=0,d=0,g=0,_=0,m=h.matrixWorldInverse;for(let p=0,S=c.length;p<S;p++){let y=c[p];if(y.isDirectionalLight){let v=n.directional[u];v.direction.setFromMatrixPosition(y.matrixWorld),i.setFromMatrixPosition(y.target.matrixWorld),v.direction.sub(i),v.direction.transformDirection(m),u++}else if(y.isSpotLight){let v=n.spot[d];v.position.setFromMatrixPosition(y.matrixWorld),v.position.applyMatrix4(m),v.direction.setFromMatrixPosition(y.matrixWorld),i.setFromMatrixPosition(y.target.matrixWorld),v.direction.sub(i),v.direction.transformDirection(m),d++}else if(y.isRectAreaLight){let v=n.rectArea[g];v.position.setFromMatrixPosition(y.matrixWorld),v.position.applyMatrix4(m),o.identity(),r.copy(y.matrixWorld),r.premultiply(m),o.extractRotation(r),v.halfWidth.set(y.width*.5,0,0),v.halfHeight.set(0,y.height*.5,0),v.halfWidth.applyMatrix4(o),v.halfHeight.applyMatrix4(o),g++}else if(y.isPointLight){let v=n.point[f];v.position.setFromMatrixPosition(y.matrixWorld),v.position.applyMatrix4(m),f++}else if(y.isHemisphereLight){let v=n.hemi[_];v.direction.setFromMatrixPosition(y.matrixWorld),v.direction.transformDirection(m),_++}}}return{setup:a,setupView:l,state:n}}function g_(s){let t=new q1(s),e=[],n=[];function i(h){c.camera=h,e.length=0,n.length=0}function r(h){e.push(h)}function o(h){n.push(h)}function a(){t.setup(e)}function l(h){t.setupView(e,h)}let c={lightsArray:e,shadowsArray:n,camera:null,lights:t,transmissionRenderTarget:{}};return{init:i,state:c,setupLights:a,setupLightsView:l,pushLight:r,pushShadow:o}}function Z1(s){let t=new WeakMap;function e(i,r=0){let o=t.get(i),a;return o===void 0?(a=new g_(s),t.set(i,[a])):r>=o.length?(a=new g_(s),o.push(a)):a=o[r],a}function n(){t=new WeakMap}return{get:e,dispose:n}}var od=class extends br{static get type(){return"MeshDepthMaterial"}constructor(t){super(),this.isMeshDepthMaterial=!0,this.depthPacking=ny,this.map=null,this.alphaMap=null,this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.wireframe=!1,this.wireframeLinewidth=1,this.setValues(t)}copy(t){return super.copy(t),this.depthPacking=t.depthPacking,this.map=t.map,this.alphaMap=t.alphaMap,this.displacementMap=t.displacementMap,this.displacementScale=t.displacementScale,this.displacementBias=t.displacementBias,this.wireframe=t.wireframe,this.wireframeLinewidth=t.wireframeLinewidth,this}},ad=class extends br{static get type(){return"MeshDistanceMaterial"}constructor(t){super(),this.isMeshDistanceMaterial=!0,this.map=null,this.alphaMap=null,this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.setValues(t)}copy(t){return super.copy(t),this.map=t.map,this.alphaMap=t.alphaMap,this.displacementMap=t.displacementMap,this.displacementScale=t.displacementScale,this.displacementBias=t.displacementBias,this}},$1=`void main() {
	gl_Position = vec4( position, 1.0 );
}`,J1=`uniform sampler2D shadow_pass;
uniform vec2 resolution;
uniform float radius;
#include <packing>
void main() {
	const float samples = float( VSM_SAMPLES );
	float mean = 0.0;
	float squared_mean = 0.0;
	float uvStride = samples <= 1.0 ? 0.0 : 2.0 / ( samples - 1.0 );
	float uvStart = samples <= 1.0 ? 0.0 : - 1.0;
	for ( float i = 0.0; i < samples; i ++ ) {
		float uvOffset = uvStart + i * uvStride;
		#ifdef HORIZONTAL_PASS
			vec2 distribution = unpackRGBATo2Half( texture2D( shadow_pass, ( gl_FragCoord.xy + vec2( uvOffset, 0.0 ) * radius ) / resolution ) );
			mean += distribution.x;
			squared_mean += distribution.y * distribution.y + distribution.x * distribution.x;
		#else
			float depth = unpackRGBAToDepth( texture2D( shadow_pass, ( gl_FragCoord.xy + vec2( 0.0, uvOffset ) * radius ) / resolution ) );
			mean += depth;
			squared_mean += depth * depth;
		#endif
	}
	mean = mean / samples;
	squared_mean = squared_mean / samples;
	float std_dev = sqrt( squared_mean - mean * mean );
	gl_FragColor = pack2HalfToRGBA( vec2( mean, std_dev ) );
}`;function K1(s,t,e){let n=new Va,i=new vt,r=new vt,o=new Ae,a=new od({depthPacking:iy}),l=new ad,c={},h=e.maxTextureSize,u={[Bs]:wn,[wn]:Bs,[pi]:pi},f=new je({defines:{VSM_SAMPLES:8},uniforms:{shadow_pass:{value:null},resolution:{value:new vt},radius:{value:4}},vertexShader:$1,fragmentShader:J1}),d=f.clone();d.defines.HORIZONTAL_PASS=1;let g=new Ei;g.setAttribute("position",new ti(new Float32Array([-1,-1,.5,3,-1,.5,-1,3,.5]),3));let _=new ve(g,f),m=this;this.enabled=!1,this.autoUpdate=!0,this.needsUpdate=!1,this.type=C_;let p=this.type;this.render=function(A,T,R){if(m.enabled===!1||m.autoUpdate===!1&&m.needsUpdate===!1||A.length===0)return;let M=s.getRenderTarget(),x=s.getActiveCubeFace(),L=s.getActiveMipmapLevel(),U=s.state;U.setBlending(ki),U.buffers.color.setClear(1,1,1,1),U.buffers.depth.setTest(!0),U.setScissorTest(!1);let F=p!==ns&&this.type===ns,z=p===ns&&this.type!==ns;for(let q=0,H=A.length;q<H;q++){let W=A[q],V=W.shadow;if(V===void 0){console.warn("THREE.WebGLShadowMap:",W,"has no shadow.");continue}if(V.autoUpdate===!1&&V.needsUpdate===!1)continue;i.copy(V.mapSize);let st=V.getFrameExtents();if(i.multiply(st),r.copy(V.mapSize),(i.x>h||i.y>h)&&(i.x>h&&(r.x=Math.floor(h/st.x),i.x=r.x*st.x,V.mapSize.x=r.x),i.y>h&&(r.y=Math.floor(h/st.y),i.y=r.y*st.y,V.mapSize.y=r.y)),V.map===null||F===!0||z===!0){let at=this.type!==ns?{minFilter:jn,magFilter:jn}:{};V.map!==null&&V.map.dispose(),V.map=new un(i.x,i.y,at),V.map.texture.name=W.name+".shadowMap",V.camera.updateProjectionMatrix()}s.setRenderTarget(V.map),s.clear();let I=V.getViewportCount();for(let at=0;at<I;at++){let Dt=V.getViewport(at);o.set(r.x*Dt.x,r.y*Dt.y,r.x*Dt.z,r.y*Dt.w),U.viewport(o),V.updateMatrices(W,at),n=V.getFrustum(),v(T,R,V.camera,W,this.type)}V.isPointLightShadow!==!0&&this.type===ns&&S(V,R),V.needsUpdate=!1}p=this.type,m.needsUpdate=!1,s.setRenderTarget(M,x,L)};function S(A,T){let R=t.update(_);f.defines.VSM_SAMPLES!==A.blurSamples&&(f.defines.VSM_SAMPLES=A.blurSamples,d.defines.VSM_SAMPLES=A.blurSamples,f.needsUpdate=!0,d.needsUpdate=!0),A.mapPass===null&&(A.mapPass=new un(i.x,i.y)),f.uniforms.shadow_pass.value=A.map.texture,f.uniforms.resolution.value=A.mapSize,f.uniforms.radius.value=A.radius,s.setRenderTarget(A.mapPass),s.clear(),s.renderBufferDirect(T,null,R,f,_,null),d.uniforms.shadow_pass.value=A.mapPass.texture,d.uniforms.resolution.value=A.mapSize,d.uniforms.radius.value=A.radius,s.setRenderTarget(A.map),s.clear(),s.renderBufferDirect(T,null,R,d,_,null)}function y(A,T,R,M){let x=null,L=R.isPointLight===!0?A.customDistanceMaterial:A.customDepthMaterial;if(L!==void 0)x=L;else if(x=R.isPointLight===!0?l:a,s.localClippingEnabled&&T.clipShadows===!0&&Array.isArray(T.clippingPlanes)&&T.clippingPlanes.length!==0||T.displacementMap&&T.displacementScale!==0||T.alphaMap&&T.alphaTest>0||T.map&&T.alphaTest>0){let U=x.uuid,F=T.uuid,z=c[U];z===void 0&&(z={},c[U]=z);let q=z[F];q===void 0&&(q=x.clone(),z[F]=q,T.addEventListener("dispose",E)),x=q}if(x.visible=T.visible,x.wireframe=T.wireframe,M===ns?x.side=T.shadowSide!==null?T.shadowSide:T.side:x.side=T.shadowSide!==null?T.shadowSide:u[T.side],x.alphaMap=T.alphaMap,x.alphaTest=T.alphaTest,x.map=T.map,x.clipShadows=T.clipShadows,x.clippingPlanes=T.clippingPlanes,x.clipIntersection=T.clipIntersection,x.displacementMap=T.displacementMap,x.displacementScale=T.displacementScale,x.displacementBias=T.displacementBias,x.wireframeLinewidth=T.wireframeLinewidth,x.linewidth=T.linewidth,R.isPointLight===!0&&x.isMeshDistanceMaterial===!0){let U=s.properties.get(x);U.light=R}return x}function v(A,T,R,M,x){if(A.visible===!1)return;if(A.layers.test(T.layers)&&(A.isMesh||A.isLine||A.isPoints)&&(A.castShadow||A.receiveShadow&&x===ns)&&(!A.frustumCulled||n.intersectsObject(A))){A.modelViewMatrix.multiplyMatrices(R.matrixWorldInverse,A.matrixWorld);let F=t.update(A),z=A.material;if(Array.isArray(z)){let q=F.groups;for(let H=0,W=q.length;H<W;H++){let V=q[H],st=z[V.materialIndex];if(st&&st.visible){let I=y(A,st,M,x);A.onBeforeShadow(s,A,T,R,F,I,V),s.renderBufferDirect(R,null,F,I,A,V),A.onAfterShadow(s,A,T,R,F,I,V)}}}else if(z.visible){let q=y(A,z,M,x);A.onBeforeShadow(s,A,T,R,F,q,null),s.renderBufferDirect(R,null,F,q,A,null),A.onAfterShadow(s,A,T,R,F,q,null)}}let U=A.children;for(let F=0,z=U.length;F<z;F++)v(U[F],T,R,M,x)}function E(A){A.target.removeEventListener("dispose",E);for(let R in c){let M=c[R],x=A.target.uuid;x in M&&(M[x].dispose(),delete M[x])}}}var Q1={[cf]:hf,[uf]:pf,[ff]:mf,[wo]:df,[hf]:cf,[pf]:uf,[mf]:ff,[df]:wo};function j1(s,t){function e(){let D=!1,yt=new Ae,$=null,tt=new Ae(0,0,0,0);return{setMask:function(Mt){$!==Mt&&!D&&(s.colorMask(Mt,Mt,Mt,Mt),$=Mt)},setLocked:function(Mt){D=Mt},setClear:function(Mt,wt,K,ft,Ut){Ut===!0&&(Mt*=ft,wt*=ft,K*=ft),yt.set(Mt,wt,K,ft),tt.equals(yt)===!1&&(s.clearColor(Mt,wt,K,ft),tt.copy(yt))},reset:function(){D=!1,$=null,tt.set(-1,0,0,0)}}}function n(){let D=!1,yt=!1,$=null,tt=null,Mt=null;return{setReversed:function(wt){if(yt!==wt){let K=t.get("EXT_clip_control");yt?K.clipControlEXT(K.LOWER_LEFT_EXT,K.ZERO_TO_ONE_EXT):K.clipControlEXT(K.LOWER_LEFT_EXT,K.NEGATIVE_ONE_TO_ONE_EXT);let ft=Mt;Mt=null,this.setClear(ft)}yt=wt},getReversed:function(){return yt},setTest:function(wt){wt?ot(s.DEPTH_TEST):Rt(s.DEPTH_TEST)},setMask:function(wt){$!==wt&&!D&&(s.depthMask(wt),$=wt)},setFunc:function(wt){if(yt&&(wt=Q1[wt]),tt!==wt){switch(wt){case cf:s.depthFunc(s.NEVER);break;case hf:s.depthFunc(s.ALWAYS);break;case uf:s.depthFunc(s.LESS);break;case wo:s.depthFunc(s.LEQUAL);break;case ff:s.depthFunc(s.EQUAL);break;case df:s.depthFunc(s.GEQUAL);break;case pf:s.depthFunc(s.GREATER);break;case mf:s.depthFunc(s.NOTEQUAL);break;default:s.depthFunc(s.LEQUAL)}tt=wt}},setLocked:function(wt){D=wt},setClear:function(wt){Mt!==wt&&(yt&&(wt=1-wt),s.clearDepth(wt),Mt=wt)},reset:function(){D=!1,$=null,tt=null,Mt=null,yt=!1}}}function i(){let D=!1,yt=null,$=null,tt=null,Mt=null,wt=null,K=null,ft=null,Ut=null;return{setTest:function(J){D||(J?ot(s.STENCIL_TEST):Rt(s.STENCIL_TEST))},setMask:function(J){yt!==J&&!D&&(s.stencilMask(J),yt=J)},setFunc:function(J,ht,Tt){($!==J||tt!==ht||Mt!==Tt)&&(s.stencilFunc(J,ht,Tt),$=J,tt=ht,Mt=Tt)},setOp:function(J,ht,Tt){(wt!==J||K!==ht||ft!==Tt)&&(s.stencilOp(J,ht,Tt),wt=J,K=ht,ft=Tt)},setLocked:function(J){D=J},setClear:function(J){Ut!==J&&(s.clearStencil(J),Ut=J)},reset:function(){D=!1,yt=null,$=null,tt=null,Mt=null,wt=null,K=null,ft=null,Ut=null}}}let r=new e,o=new n,a=new i,l=new WeakMap,c=new WeakMap,h={},u={},f=new WeakMap,d=[],g=null,_=!1,m=null,p=null,S=null,y=null,v=null,E=null,A=null,T=new se(0,0,0),R=0,M=!1,x=null,L=null,U=null,F=null,z=null,q=s.getParameter(s.MAX_COMBINED_TEXTURE_IMAGE_UNITS),H=!1,W=0,V=s.getParameter(s.VERSION);V.indexOf("WebGL")!==-1?(W=parseFloat(/^WebGL (\d)/.exec(V)[1]),H=W>=1):V.indexOf("OpenGL ES")!==-1&&(W=parseFloat(/^OpenGL ES (\d)/.exec(V)[1]),H=W>=2);let st=null,I={},at=s.getParameter(s.SCISSOR_BOX),Dt=s.getParameter(s.VIEWPORT),Vt=new Ae().fromArray(at),Z=new Ae().fromArray(Dt);function rt(D,yt,$,tt){let Mt=new Uint8Array(4),wt=s.createTexture();s.bindTexture(D,wt),s.texParameteri(D,s.TEXTURE_MIN_FILTER,s.NEAREST),s.texParameteri(D,s.TEXTURE_MAG_FILTER,s.NEAREST);for(let K=0;K<$;K++)D===s.TEXTURE_3D||D===s.TEXTURE_2D_ARRAY?s.texImage3D(yt,0,s.RGBA,1,1,tt,0,s.RGBA,s.UNSIGNED_BYTE,Mt):s.texImage2D(yt+K,0,s.RGBA,1,1,0,s.RGBA,s.UNSIGNED_BYTE,Mt);return wt}let St={};St[s.TEXTURE_2D]=rt(s.TEXTURE_2D,s.TEXTURE_2D,1),St[s.TEXTURE_CUBE_MAP]=rt(s.TEXTURE_CUBE_MAP,s.TEXTURE_CUBE_MAP_POSITIVE_X,6),St[s.TEXTURE_2D_ARRAY]=rt(s.TEXTURE_2D_ARRAY,s.TEXTURE_2D_ARRAY,1,1),St[s.TEXTURE_3D]=rt(s.TEXTURE_3D,s.TEXTURE_3D,1,1),r.setClear(0,0,0,1),o.setClear(1),a.setClear(0),ot(s.DEPTH_TEST),o.setFunc(wo),lt(!1),O(xg),ot(s.CULL_FACE),P(ki);function ot(D){h[D]!==!0&&(s.enable(D),h[D]=!0)}function Rt(D){h[D]!==!1&&(s.disable(D),h[D]=!1)}function Bt(D,yt){return u[D]!==yt?(s.bindFramebuffer(D,yt),u[D]=yt,D===s.DRAW_FRAMEBUFFER&&(u[s.FRAMEBUFFER]=yt),D===s.FRAMEBUFFER&&(u[s.DRAW_FRAMEBUFFER]=yt),!0):!1}function Wt(D,yt){let $=d,tt=!1;if(D){$=f.get(yt),$===void 0&&($=[],f.set(yt,$));let Mt=D.textures;if($.length!==Mt.length||$[0]!==s.COLOR_ATTACHMENT0){for(let wt=0,K=Mt.length;wt<K;wt++)$[wt]=s.COLOR_ATTACHMENT0+wt;$.length=Mt.length,tt=!0}}else $[0]!==s.BACK&&($[0]=s.BACK,tt=!0);tt&&s.drawBuffers($)}function Xt(D){return g!==D?(s.useProgram(D),g=D,!0):!1}let et={[gr]:s.FUNC_ADD,[Nx]:s.FUNC_SUBTRACT,[Ox]:s.FUNC_REVERSE_SUBTRACT};et[Fx]=s.MIN,et[Bx]=s.MAX;let nt={[kx]:s.ZERO,[zx]:s.ONE,[Vx]:s.SRC_COLOR,[af]:s.SRC_ALPHA,[qx]:s.SRC_ALPHA_SATURATE,[Xx]:s.DST_COLOR,[Gx]:s.DST_ALPHA,[Hx]:s.ONE_MINUS_SRC_COLOR,[lf]:s.ONE_MINUS_SRC_ALPHA,[Yx]:s.ONE_MINUS_DST_COLOR,[Wx]:s.ONE_MINUS_DST_ALPHA,[Zx]:s.CONSTANT_COLOR,[$x]:s.ONE_MINUS_CONSTANT_COLOR,[Jx]:s.CONSTANT_ALPHA,[Kx]:s.ONE_MINUS_CONSTANT_ALPHA};function P(D,yt,$,tt,Mt,wt,K,ft,Ut,J){if(D===ki){_===!0&&(Rt(s.BLEND),_=!1);return}if(_===!1&&(ot(s.BLEND),_=!0),D!==Ux){if(D!==m||J!==M){if((p!==gr||v!==gr)&&(s.blendEquation(s.FUNC_ADD),p=gr,v=gr),J)switch(D){case yo:s.blendFuncSeparate(s.ONE,s.ONE_MINUS_SRC_ALPHA,s.ONE,s.ONE_MINUS_SRC_ALPHA);break;case Mc:s.blendFunc(s.ONE,s.ONE);break;case yg:s.blendFuncSeparate(s.ZERO,s.ONE_MINUS_SRC_COLOR,s.ZERO,s.ONE);break;case Mg:s.blendFuncSeparate(s.ZERO,s.SRC_COLOR,s.ZERO,s.SRC_ALPHA);break;default:console.error("THREE.WebGLState: Invalid blending: ",D);break}else switch(D){case yo:s.blendFuncSeparate(s.SRC_ALPHA,s.ONE_MINUS_SRC_ALPHA,s.ONE,s.ONE_MINUS_SRC_ALPHA);break;case Mc:s.blendFunc(s.SRC_ALPHA,s.ONE);break;case yg:s.blendFuncSeparate(s.ZERO,s.ONE_MINUS_SRC_COLOR,s.ZERO,s.ONE);break;case Mg:s.blendFunc(s.ZERO,s.SRC_COLOR);break;default:console.error("THREE.WebGLState: Invalid blending: ",D);break}S=null,y=null,E=null,A=null,T.set(0,0,0),R=0,m=D,M=J}return}Mt=Mt||yt,wt=wt||$,K=K||tt,(yt!==p||Mt!==v)&&(s.blendEquationSeparate(et[yt],et[Mt]),p=yt,v=Mt),($!==S||tt!==y||wt!==E||K!==A)&&(s.blendFuncSeparate(nt[$],nt[tt],nt[wt],nt[K]),S=$,y=tt,E=wt,A=K),(ft.equals(T)===!1||Ut!==R)&&(s.blendColor(ft.r,ft.g,ft.b,Ut),T.copy(ft),R=Ut),m=D,M=!1}function It(D,yt){D.side===pi?Rt(s.CULL_FACE):ot(s.CULL_FACE);let $=D.side===wn;yt&&($=!$),lt($),D.blending===yo&&D.transparent===!1?P(ki):P(D.blending,D.blendEquation,D.blendSrc,D.blendDst,D.blendEquationAlpha,D.blendSrcAlpha,D.blendDstAlpha,D.blendColor,D.blendAlpha,D.premultipliedAlpha),o.setFunc(D.depthFunc),o.setTest(D.depthTest),o.setMask(D.depthWrite),r.setMask(D.colorWrite);let tt=D.stencilWrite;a.setTest(tt),tt&&(a.setMask(D.stencilWriteMask),a.setFunc(D.stencilFunc,D.stencilRef,D.stencilFuncMask),a.setOp(D.stencilFail,D.stencilZFail,D.stencilZPass)),zt(D.polygonOffset,D.polygonOffsetFactor,D.polygonOffsetUnits),D.alphaToCoverage===!0?ot(s.SAMPLE_ALPHA_TO_COVERAGE):Rt(s.SAMPLE_ALPHA_TO_COVERAGE)}function lt(D){x!==D&&(D?s.frontFace(s.CW):s.frontFace(s.CCW),x=D)}function O(D){D!==Ix?(ot(s.CULL_FACE),D!==L&&(D===xg?s.cullFace(s.BACK):D===Lx?s.cullFace(s.FRONT):s.cullFace(s.FRONT_AND_BACK))):Rt(s.CULL_FACE),L=D}function dt(D){D!==U&&(H&&s.lineWidth(D),U=D)}function zt(D,yt,$){D?(ot(s.POLYGON_OFFSET_FILL),(F!==yt||z!==$)&&(s.polygonOffset(yt,$),F=yt,z=$)):Rt(s.POLYGON_OFFSET_FILL)}function At(D){D?ot(s.SCISSOR_TEST):Rt(s.SCISSOR_TEST)}function C(D){D===void 0&&(D=s.TEXTURE0+q-1),st!==D&&(s.activeTexture(D),st=D)}function b(D,yt,$){$===void 0&&(st===null?$=s.TEXTURE0+q-1:$=st);let tt=I[$];tt===void 0&&(tt={type:void 0,texture:void 0},I[$]=tt),(tt.type!==D||tt.texture!==yt)&&(st!==$&&(s.activeTexture($),st=$),s.bindTexture(D,yt||St[D]),tt.type=D,tt.texture=yt)}function X(){let D=I[st];D!==void 0&&D.type!==void 0&&(s.bindTexture(D.type,null),D.type=void 0,D.texture=void 0)}function Q(){try{s.compressedTexImage2D.apply(s,arguments)}catch(D){console.error("THREE.WebGLState:",D)}}function it(){try{s.compressedTexImage3D.apply(s,arguments)}catch(D){console.error("THREE.WebGLState:",D)}}function j(){try{s.texSubImage2D.apply(s,arguments)}catch(D){console.error("THREE.WebGLState:",D)}}function xt(){try{s.texSubImage3D.apply(s,arguments)}catch(D){console.error("THREE.WebGLState:",D)}}function pt(){try{s.compressedTexSubImage2D.apply(s,arguments)}catch(D){console.error("THREE.WebGLState:",D)}}function bt(){try{s.compressedTexSubImage3D.apply(s,arguments)}catch(D){console.error("THREE.WebGLState:",D)}}function Kt(){try{s.texStorage2D.apply(s,arguments)}catch(D){console.error("THREE.WebGLState:",D)}}function ut(){try{s.texStorage3D.apply(s,arguments)}catch(D){console.error("THREE.WebGLState:",D)}}function gt(){try{s.texImage2D.apply(s,arguments)}catch(D){console.error("THREE.WebGLState:",D)}}function qt(){try{s.texImage3D.apply(s,arguments)}catch(D){console.error("THREE.WebGLState:",D)}}function Yt(D){Vt.equals(D)===!1&&(s.scissor(D.x,D.y,D.z,D.w),Vt.copy(D))}function Lt(D){Z.equals(D)===!1&&(s.viewport(D.x,D.y,D.z,D.w),Z.copy(D))}function ee(D,yt){let $=c.get(yt);$===void 0&&($=new WeakMap,c.set(yt,$));let tt=$.get(D);tt===void 0&&(tt=s.getUniformBlockIndex(yt,D.name),$.set(D,tt))}function Jt(D,yt){let tt=c.get(yt).get(D);l.get(yt)!==tt&&(s.uniformBlockBinding(yt,tt,D.__bindingPointIndex),l.set(yt,tt))}function Qt(){s.disable(s.BLEND),s.disable(s.CULL_FACE),s.disable(s.DEPTH_TEST),s.disable(s.POLYGON_OFFSET_FILL),s.disable(s.SCISSOR_TEST),s.disable(s.STENCIL_TEST),s.disable(s.SAMPLE_ALPHA_TO_COVERAGE),s.blendEquation(s.FUNC_ADD),s.blendFunc(s.ONE,s.ZERO),s.blendFuncSeparate(s.ONE,s.ZERO,s.ONE,s.ZERO),s.blendColor(0,0,0,0),s.colorMask(!0,!0,!0,!0),s.clearColor(0,0,0,0),s.depthMask(!0),s.depthFunc(s.LESS),o.setReversed(!1),s.clearDepth(1),s.stencilMask(4294967295),s.stencilFunc(s.ALWAYS,0,4294967295),s.stencilOp(s.KEEP,s.KEEP,s.KEEP),s.clearStencil(0),s.cullFace(s.BACK),s.frontFace(s.CCW),s.polygonOffset(0,0),s.activeTexture(s.TEXTURE0),s.bindFramebuffer(s.FRAMEBUFFER,null),s.bindFramebuffer(s.DRAW_FRAMEBUFFER,null),s.bindFramebuffer(s.READ_FRAMEBUFFER,null),s.useProgram(null),s.lineWidth(1),s.scissor(0,0,s.canvas.width,s.canvas.height),s.viewport(0,0,s.canvas.width,s.canvas.height),h={},st=null,I={},u={},f=new WeakMap,d=[],g=null,_=!1,m=null,p=null,S=null,y=null,v=null,E=null,A=null,T=new se(0,0,0),R=0,M=!1,x=null,L=null,U=null,F=null,z=null,Vt.set(0,0,s.canvas.width,s.canvas.height),Z.set(0,0,s.canvas.width,s.canvas.height),r.reset(),o.reset(),a.reset()}return{buffers:{color:r,depth:o,stencil:a},enable:ot,disable:Rt,bindFramebuffer:Bt,drawBuffers:Wt,useProgram:Xt,setBlending:P,setMaterial:It,setFlipSided:lt,setCullFace:O,setLineWidth:dt,setPolygonOffset:zt,setScissorTest:At,activeTexture:C,bindTexture:b,unbindTexture:X,compressedTexImage2D:Q,compressedTexImage3D:it,texImage2D:gt,texImage3D:qt,updateUBOMapping:ee,uniformBlockBinding:Jt,texStorage2D:Kt,texStorage3D:ut,texSubImage2D:j,texSubImage3D:xt,compressedTexSubImage2D:pt,compressedTexSubImage3D:bt,scissor:Yt,viewport:Lt,reset:Qt}}function __(s,t,e,n){let i=tw(n);switch(e){case U_:return s*t;case O_:return s*t;case F_:return s*t*2;case Vd:return s*t/i.components*i.byteLength;case Hd:return s*t/i.components*i.byteLength;case B_:return s*t*2/i.components*i.byteLength;case Gd:return s*t*2/i.components*i.byteLength;case N_:return s*t*3/i.components*i.byteLength;case bi:return s*t*4/i.components*i.byteLength;case Wd:return s*t*4/i.components*i.byteLength;case gc:case _c:return Math.floor((s+3)/4)*Math.floor((t+3)/4)*8;case vc:case xc:return Math.floor((s+3)/4)*Math.floor((t+3)/4)*16;case Mf:case bf:return Math.max(s,16)*Math.max(t,8)/4;case yf:case Sf:return Math.max(s,8)*Math.max(t,8)/2;case wf:case Tf:return Math.floor((s+3)/4)*Math.floor((t+3)/4)*8;case Ef:return Math.floor((s+3)/4)*Math.floor((t+3)/4)*16;case Af:return Math.floor((s+3)/4)*Math.floor((t+3)/4)*16;case Cf:return Math.floor((s+4)/5)*Math.floor((t+3)/4)*16;case Rf:return Math.floor((s+4)/5)*Math.floor((t+4)/5)*16;case Pf:return Math.floor((s+5)/6)*Math.floor((t+4)/5)*16;case If:return Math.floor((s+5)/6)*Math.floor((t+5)/6)*16;case Lf:return Math.floor((s+7)/8)*Math.floor((t+4)/5)*16;case Df:return Math.floor((s+7)/8)*Math.floor((t+5)/6)*16;case Uf:return Math.floor((s+7)/8)*Math.floor((t+7)/8)*16;case Nf:return Math.floor((s+9)/10)*Math.floor((t+4)/5)*16;case Of:return Math.floor((s+9)/10)*Math.floor((t+5)/6)*16;case Ff:return Math.floor((s+9)/10)*Math.floor((t+7)/8)*16;case Bf:return Math.floor((s+9)/10)*Math.floor((t+9)/10)*16;case kf:return Math.floor((s+11)/12)*Math.floor((t+9)/10)*16;case zf:return Math.floor((s+11)/12)*Math.floor((t+11)/12)*16;case yc:case Vf:case Hf:return Math.ceil(s/4)*Math.ceil(t/4)*16;case k_:case Gf:return Math.ceil(s/4)*Math.ceil(t/4)*8;case Wf:case Xf:return Math.ceil(s/4)*Math.ceil(t/4)*16}throw new Error(`Unable to determine texture byte length for ${e} format.`)}function tw(s){switch(s){case os:case I_:return{byteLength:1,components:1};case za:case L_:case ei:return{byteLength:2,components:1};case kd:case zd:return{byteLength:2,components:4};case Mr:case Bd:case Bi:return{byteLength:4,components:1};case D_:return{byteLength:4,components:3}}throw new Error(`Unknown texture type ${s}.`)}function ew(s,t,e,n,i,r,o){let a=t.has("WEBGL_multisampled_render_to_texture")?t.get("WEBGL_multisampled_render_to_texture"):null,l=typeof navigator>"u"?!1:/OculusBrowser/g.test(navigator.userAgent),c=new vt,h=new WeakMap,u,f=new WeakMap,d=!1;try{d=typeof OffscreenCanvas<"u"&&new OffscreenCanvas(1,1).getContext("2d")!==null}catch{}function g(C,b){return d?new OffscreenCanvas(C,b):wc("canvas")}function _(C,b,X){let Q=1,it=At(C);if((it.width>X||it.height>X)&&(Q=X/Math.max(it.width,it.height)),Q<1)if(typeof HTMLImageElement<"u"&&C instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&C instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&C instanceof ImageBitmap||typeof VideoFrame<"u"&&C instanceof VideoFrame){let j=Math.floor(Q*it.width),xt=Math.floor(Q*it.height);u===void 0&&(u=g(j,xt));let pt=b?g(j,xt):u;return pt.width=j,pt.height=xt,pt.getContext("2d").drawImage(C,0,0,j,xt),console.warn("THREE.WebGLRenderer: Texture has been resized from ("+it.width+"x"+it.height+") to ("+j+"x"+xt+")."),pt}else return"data"in C&&console.warn("THREE.WebGLRenderer: Image in DataTexture is too big ("+it.width+"x"+it.height+")."),C;return C}function m(C){return C.generateMipmaps}function p(C){s.generateMipmap(C)}function S(C){return C.isWebGLCubeRenderTarget?s.TEXTURE_CUBE_MAP:C.isWebGL3DRenderTarget?s.TEXTURE_3D:C.isWebGLArrayRenderTarget||C.isCompressedArrayTexture?s.TEXTURE_2D_ARRAY:s.TEXTURE_2D}function y(C,b,X,Q,it=!1){if(C!==null){if(s[C]!==void 0)return s[C];console.warn("THREE.WebGLRenderer: Attempt to use non-existing WebGL internal format '"+C+"'")}let j=b;if(b===s.RED&&(X===s.FLOAT&&(j=s.R32F),X===s.HALF_FLOAT&&(j=s.R16F),X===s.UNSIGNED_BYTE&&(j=s.R8)),b===s.RED_INTEGER&&(X===s.UNSIGNED_BYTE&&(j=s.R8UI),X===s.UNSIGNED_SHORT&&(j=s.R16UI),X===s.UNSIGNED_INT&&(j=s.R32UI),X===s.BYTE&&(j=s.R8I),X===s.SHORT&&(j=s.R16I),X===s.INT&&(j=s.R32I)),b===s.RG&&(X===s.FLOAT&&(j=s.RG32F),X===s.HALF_FLOAT&&(j=s.RG16F),X===s.UNSIGNED_BYTE&&(j=s.RG8)),b===s.RG_INTEGER&&(X===s.UNSIGNED_BYTE&&(j=s.RG8UI),X===s.UNSIGNED_SHORT&&(j=s.RG16UI),X===s.UNSIGNED_INT&&(j=s.RG32UI),X===s.BYTE&&(j=s.RG8I),X===s.SHORT&&(j=s.RG16I),X===s.INT&&(j=s.RG32I)),b===s.RGB_INTEGER&&(X===s.UNSIGNED_BYTE&&(j=s.RGB8UI),X===s.UNSIGNED_SHORT&&(j=s.RGB16UI),X===s.UNSIGNED_INT&&(j=s.RGB32UI),X===s.BYTE&&(j=s.RGB8I),X===s.SHORT&&(j=s.RGB16I),X===s.INT&&(j=s.RGB32I)),b===s.RGBA_INTEGER&&(X===s.UNSIGNED_BYTE&&(j=s.RGBA8UI),X===s.UNSIGNED_SHORT&&(j=s.RGBA16UI),X===s.UNSIGNED_INT&&(j=s.RGBA32UI),X===s.BYTE&&(j=s.RGBA8I),X===s.SHORT&&(j=s.RGBA16I),X===s.INT&&(j=s.RGBA32I)),b===s.RGB&&X===s.UNSIGNED_INT_5_9_9_9_REV&&(j=s.RGB9_E5),b===s.RGBA){let xt=it?$c:ge.getTransfer(Q);X===s.FLOAT&&(j=s.RGBA32F),X===s.HALF_FLOAT&&(j=s.RGBA16F),X===s.UNSIGNED_BYTE&&(j=xt===we?s.SRGB8_ALPHA8:s.RGBA8),X===s.UNSIGNED_SHORT_4_4_4_4&&(j=s.RGBA4),X===s.UNSIGNED_SHORT_5_5_5_1&&(j=s.RGB5_A1)}return(j===s.R16F||j===s.R32F||j===s.RG16F||j===s.RG32F||j===s.RGBA16F||j===s.RGBA32F)&&t.get("EXT_color_buffer_float"),j}function v(C,b){let X;return C?b===null||b===Mr||b===Ao?X=s.DEPTH24_STENCIL8:b===Bi?X=s.DEPTH32F_STENCIL8:b===za&&(X=s.DEPTH24_STENCIL8,console.warn("DepthTexture: 16 bit depth attachment is not supported with stencil. Using 24-bit attachment.")):b===null||b===Mr||b===Ao?X=s.DEPTH_COMPONENT24:b===Bi?X=s.DEPTH_COMPONENT32F:b===za&&(X=s.DEPTH_COMPONENT16),X}function E(C,b){return m(C)===!0||C.isFramebufferTexture&&C.minFilter!==jn&&C.minFilter!==Fi?Math.log2(Math.max(b.width,b.height))+1:C.mipmaps!==void 0&&C.mipmaps.length>0?C.mipmaps.length:C.isCompressedTexture&&Array.isArray(C.image)?b.mipmaps.length:1}function A(C){let b=C.target;b.removeEventListener("dispose",A),R(b),b.isVideoTexture&&h.delete(b)}function T(C){let b=C.target;b.removeEventListener("dispose",T),x(b)}function R(C){let b=n.get(C);if(b.__webglInit===void 0)return;let X=C.source,Q=f.get(X);if(Q){let it=Q[b.__cacheKey];it.usedTimes--,it.usedTimes===0&&M(C),Object.keys(Q).length===0&&f.delete(X)}n.remove(C)}function M(C){let b=n.get(C);s.deleteTexture(b.__webglTexture);let X=C.source,Q=f.get(X);delete Q[b.__cacheKey],o.memory.textures--}function x(C){let b=n.get(C);if(C.depthTexture&&(C.depthTexture.dispose(),n.remove(C.depthTexture)),C.isWebGLCubeRenderTarget)for(let Q=0;Q<6;Q++){if(Array.isArray(b.__webglFramebuffer[Q]))for(let it=0;it<b.__webglFramebuffer[Q].length;it++)s.deleteFramebuffer(b.__webglFramebuffer[Q][it]);else s.deleteFramebuffer(b.__webglFramebuffer[Q]);b.__webglDepthbuffer&&s.deleteRenderbuffer(b.__webglDepthbuffer[Q])}else{if(Array.isArray(b.__webglFramebuffer))for(let Q=0;Q<b.__webglFramebuffer.length;Q++)s.deleteFramebuffer(b.__webglFramebuffer[Q]);else s.deleteFramebuffer(b.__webglFramebuffer);if(b.__webglDepthbuffer&&s.deleteRenderbuffer(b.__webglDepthbuffer),b.__webglMultisampledFramebuffer&&s.deleteFramebuffer(b.__webglMultisampledFramebuffer),b.__webglColorRenderbuffer)for(let Q=0;Q<b.__webglColorRenderbuffer.length;Q++)b.__webglColorRenderbuffer[Q]&&s.deleteRenderbuffer(b.__webglColorRenderbuffer[Q]);b.__webglDepthRenderbuffer&&s.deleteRenderbuffer(b.__webglDepthRenderbuffer)}let X=C.textures;for(let Q=0,it=X.length;Q<it;Q++){let j=n.get(X[Q]);j.__webglTexture&&(s.deleteTexture(j.__webglTexture),o.memory.textures--),n.remove(X[Q])}n.remove(C)}let L=0;function U(){L=0}function F(){let C=L;return C>=i.maxTextures&&console.warn("THREE.WebGLTextures: Trying to use "+C+" texture units while this GPU supports only "+i.maxTextures),L+=1,C}function z(C){let b=[];return b.push(C.wrapS),b.push(C.wrapT),b.push(C.wrapR||0),b.push(C.magFilter),b.push(C.minFilter),b.push(C.anisotropy),b.push(C.internalFormat),b.push(C.format),b.push(C.type),b.push(C.generateMipmaps),b.push(C.premultiplyAlpha),b.push(C.flipY),b.push(C.unpackAlignment),b.push(C.colorSpace),b.join()}function q(C,b){let X=n.get(C);if(C.isVideoTexture&&dt(C),C.isRenderTargetTexture===!1&&C.version>0&&X.__version!==C.version){let Q=C.image;if(Q===null)console.warn("THREE.WebGLRenderer: Texture marked for update but no image data found.");else if(Q.complete===!1)console.warn("THREE.WebGLRenderer: Texture marked for update but image is incomplete");else{Z(X,C,b);return}}e.bindTexture(s.TEXTURE_2D,X.__webglTexture,s.TEXTURE0+b)}function H(C,b){let X=n.get(C);if(C.version>0&&X.__version!==C.version){Z(X,C,b);return}e.bindTexture(s.TEXTURE_2D_ARRAY,X.__webglTexture,s.TEXTURE0+b)}function W(C,b){let X=n.get(C);if(C.version>0&&X.__version!==C.version){Z(X,C,b);return}e.bindTexture(s.TEXTURE_3D,X.__webglTexture,s.TEXTURE0+b)}function V(C,b){let X=n.get(C);if(C.version>0&&X.__version!==C.version){rt(X,C,b);return}e.bindTexture(s.TEXTURE_CUBE_MAP,X.__webglTexture,s.TEXTURE0+b)}let st={[vf]:s.REPEAT,[xr]:s.CLAMP_TO_EDGE,[xf]:s.MIRRORED_REPEAT},I={[jn]:s.NEAREST,[ey]:s.NEAREST_MIPMAP_NEAREST,[Wl]:s.NEAREST_MIPMAP_LINEAR,[Fi]:s.LINEAR,[Tu]:s.LINEAR_MIPMAP_NEAREST,[yr]:s.LINEAR_MIPMAP_LINEAR},at={[ry]:s.NEVER,[uy]:s.ALWAYS,[oy]:s.LESS,[V_]:s.LEQUAL,[ay]:s.EQUAL,[hy]:s.GEQUAL,[ly]:s.GREATER,[cy]:s.NOTEQUAL};function Dt(C,b){if(b.type===Bi&&t.has("OES_texture_float_linear")===!1&&(b.magFilter===Fi||b.magFilter===Tu||b.magFilter===Wl||b.magFilter===yr||b.minFilter===Fi||b.minFilter===Tu||b.minFilter===Wl||b.minFilter===yr)&&console.warn("THREE.WebGLRenderer: Unable to use linear filtering with floating point textures. OES_texture_float_linear not supported on this device."),s.texParameteri(C,s.TEXTURE_WRAP_S,st[b.wrapS]),s.texParameteri(C,s.TEXTURE_WRAP_T,st[b.wrapT]),(C===s.TEXTURE_3D||C===s.TEXTURE_2D_ARRAY)&&s.texParameteri(C,s.TEXTURE_WRAP_R,st[b.wrapR]),s.texParameteri(C,s.TEXTURE_MAG_FILTER,I[b.magFilter]),s.texParameteri(C,s.TEXTURE_MIN_FILTER,I[b.minFilter]),b.compareFunction&&(s.texParameteri(C,s.TEXTURE_COMPARE_MODE,s.COMPARE_REF_TO_TEXTURE),s.texParameteri(C,s.TEXTURE_COMPARE_FUNC,at[b.compareFunction])),t.has("EXT_texture_filter_anisotropic")===!0){if(b.magFilter===jn||b.minFilter!==Wl&&b.minFilter!==yr||b.type===Bi&&t.has("OES_texture_float_linear")===!1)return;if(b.anisotropy>1||n.get(b).__currentAnisotropy){let X=t.get("EXT_texture_filter_anisotropic");s.texParameterf(C,X.TEXTURE_MAX_ANISOTROPY_EXT,Math.min(b.anisotropy,i.getMaxAnisotropy())),n.get(b).__currentAnisotropy=b.anisotropy}}}function Vt(C,b){let X=!1;C.__webglInit===void 0&&(C.__webglInit=!0,b.addEventListener("dispose",A));let Q=b.source,it=f.get(Q);it===void 0&&(it={},f.set(Q,it));let j=z(b);if(j!==C.__cacheKey){it[j]===void 0&&(it[j]={texture:s.createTexture(),usedTimes:0},o.memory.textures++,X=!0),it[j].usedTimes++;let xt=it[C.__cacheKey];xt!==void 0&&(it[C.__cacheKey].usedTimes--,xt.usedTimes===0&&M(b)),C.__cacheKey=j,C.__webglTexture=it[j].texture}return X}function Z(C,b,X){let Q=s.TEXTURE_2D;(b.isDataArrayTexture||b.isCompressedArrayTexture)&&(Q=s.TEXTURE_2D_ARRAY),b.isData3DTexture&&(Q=s.TEXTURE_3D);let it=Vt(C,b),j=b.source;e.bindTexture(Q,C.__webglTexture,s.TEXTURE0+X);let xt=n.get(j);if(j.version!==xt.__version||it===!0){e.activeTexture(s.TEXTURE0+X);let pt=ge.getPrimaries(ge.workingColorSpace),bt=b.colorSpace===Us?null:ge.getPrimaries(b.colorSpace),Kt=b.colorSpace===Us||pt===bt?s.NONE:s.BROWSER_DEFAULT_WEBGL;s.pixelStorei(s.UNPACK_FLIP_Y_WEBGL,b.flipY),s.pixelStorei(s.UNPACK_PREMULTIPLY_ALPHA_WEBGL,b.premultiplyAlpha),s.pixelStorei(s.UNPACK_ALIGNMENT,b.unpackAlignment),s.pixelStorei(s.UNPACK_COLORSPACE_CONVERSION_WEBGL,Kt);let ut=_(b.image,!1,i.maxTextureSize);ut=zt(b,ut);let gt=r.convert(b.format,b.colorSpace),qt=r.convert(b.type),Yt=y(b.internalFormat,gt,qt,b.colorSpace,b.isVideoTexture);Dt(Q,b);let Lt,ee=b.mipmaps,Jt=b.isVideoTexture!==!0,Qt=xt.__version===void 0||it===!0,D=j.dataReady,yt=E(b,ut);if(b.isDepthTexture)Yt=v(b.format===Co,b.type),Qt&&(Jt?e.texStorage2D(s.TEXTURE_2D,1,Yt,ut.width,ut.height):e.texImage2D(s.TEXTURE_2D,0,Yt,ut.width,ut.height,0,gt,qt,null));else if(b.isDataTexture)if(ee.length>0){Jt&&Qt&&e.texStorage2D(s.TEXTURE_2D,yt,Yt,ee[0].width,ee[0].height);for(let $=0,tt=ee.length;$<tt;$++)Lt=ee[$],Jt?D&&e.texSubImage2D(s.TEXTURE_2D,$,0,0,Lt.width,Lt.height,gt,qt,Lt.data):e.texImage2D(s.TEXTURE_2D,$,Yt,Lt.width,Lt.height,0,gt,qt,Lt.data);b.generateMipmaps=!1}else Jt?(Qt&&e.texStorage2D(s.TEXTURE_2D,yt,Yt,ut.width,ut.height),D&&e.texSubImage2D(s.TEXTURE_2D,0,0,0,ut.width,ut.height,gt,qt,ut.data)):e.texImage2D(s.TEXTURE_2D,0,Yt,ut.width,ut.height,0,gt,qt,ut.data);else if(b.isCompressedTexture)if(b.isCompressedArrayTexture){Jt&&Qt&&e.texStorage3D(s.TEXTURE_2D_ARRAY,yt,Yt,ee[0].width,ee[0].height,ut.depth);for(let $=0,tt=ee.length;$<tt;$++)if(Lt=ee[$],b.format!==bi)if(gt!==null)if(Jt){if(D)if(b.layerUpdates.size>0){let Mt=__(Lt.width,Lt.height,b.format,b.type);for(let wt of b.layerUpdates){let K=Lt.data.subarray(wt*Mt/Lt.data.BYTES_PER_ELEMENT,(wt+1)*Mt/Lt.data.BYTES_PER_ELEMENT);e.compressedTexSubImage3D(s.TEXTURE_2D_ARRAY,$,0,0,wt,Lt.width,Lt.height,1,gt,K)}b.clearLayerUpdates()}else e.compressedTexSubImage3D(s.TEXTURE_2D_ARRAY,$,0,0,0,Lt.width,Lt.height,ut.depth,gt,Lt.data)}else e.compressedTexImage3D(s.TEXTURE_2D_ARRAY,$,Yt,Lt.width,Lt.height,ut.depth,0,Lt.data,0,0);else console.warn("THREE.WebGLRenderer: Attempt to load unsupported compressed texture format in .uploadTexture()");else Jt?D&&e.texSubImage3D(s.TEXTURE_2D_ARRAY,$,0,0,0,Lt.width,Lt.height,ut.depth,gt,qt,Lt.data):e.texImage3D(s.TEXTURE_2D_ARRAY,$,Yt,Lt.width,Lt.height,ut.depth,0,gt,qt,Lt.data)}else{Jt&&Qt&&e.texStorage2D(s.TEXTURE_2D,yt,Yt,ee[0].width,ee[0].height);for(let $=0,tt=ee.length;$<tt;$++)Lt=ee[$],b.format!==bi?gt!==null?Jt?D&&e.compressedTexSubImage2D(s.TEXTURE_2D,$,0,0,Lt.width,Lt.height,gt,Lt.data):e.compressedTexImage2D(s.TEXTURE_2D,$,Yt,Lt.width,Lt.height,0,Lt.data):console.warn("THREE.WebGLRenderer: Attempt to load unsupported compressed texture format in .uploadTexture()"):Jt?D&&e.texSubImage2D(s.TEXTURE_2D,$,0,0,Lt.width,Lt.height,gt,qt,Lt.data):e.texImage2D(s.TEXTURE_2D,$,Yt,Lt.width,Lt.height,0,gt,qt,Lt.data)}else if(b.isDataArrayTexture)if(Jt){if(Qt&&e.texStorage3D(s.TEXTURE_2D_ARRAY,yt,Yt,ut.width,ut.height,ut.depth),D)if(b.layerUpdates.size>0){let $=__(ut.width,ut.height,b.format,b.type);for(let tt of b.layerUpdates){let Mt=ut.data.subarray(tt*$/ut.data.BYTES_PER_ELEMENT,(tt+1)*$/ut.data.BYTES_PER_ELEMENT);e.texSubImage3D(s.TEXTURE_2D_ARRAY,0,0,0,tt,ut.width,ut.height,1,gt,qt,Mt)}b.clearLayerUpdates()}else e.texSubImage3D(s.TEXTURE_2D_ARRAY,0,0,0,0,ut.width,ut.height,ut.depth,gt,qt,ut.data)}else e.texImage3D(s.TEXTURE_2D_ARRAY,0,Yt,ut.width,ut.height,ut.depth,0,gt,qt,ut.data);else if(b.isData3DTexture)Jt?(Qt&&e.texStorage3D(s.TEXTURE_3D,yt,Yt,ut.width,ut.height,ut.depth),D&&e.texSubImage3D(s.TEXTURE_3D,0,0,0,0,ut.width,ut.height,ut.depth,gt,qt,ut.data)):e.texImage3D(s.TEXTURE_3D,0,Yt,ut.width,ut.height,ut.depth,0,gt,qt,ut.data);else if(b.isFramebufferTexture){if(Qt)if(Jt)e.texStorage2D(s.TEXTURE_2D,yt,Yt,ut.width,ut.height);else{let $=ut.width,tt=ut.height;for(let Mt=0;Mt<yt;Mt++)e.texImage2D(s.TEXTURE_2D,Mt,Yt,$,tt,0,gt,qt,null),$>>=1,tt>>=1}}else if(ee.length>0){if(Jt&&Qt){let $=At(ee[0]);e.texStorage2D(s.TEXTURE_2D,yt,Yt,$.width,$.height)}for(let $=0,tt=ee.length;$<tt;$++)Lt=ee[$],Jt?D&&e.texSubImage2D(s.TEXTURE_2D,$,0,0,gt,qt,Lt):e.texImage2D(s.TEXTURE_2D,$,Yt,gt,qt,Lt);b.generateMipmaps=!1}else if(Jt){if(Qt){let $=At(ut);e.texStorage2D(s.TEXTURE_2D,yt,Yt,$.width,$.height)}D&&e.texSubImage2D(s.TEXTURE_2D,0,0,0,gt,qt,ut)}else e.texImage2D(s.TEXTURE_2D,0,Yt,gt,qt,ut);m(b)&&p(Q),xt.__version=j.version,b.onUpdate&&b.onUpdate(b)}C.__version=b.version}function rt(C,b,X){if(b.image.length!==6)return;let Q=Vt(C,b),it=b.source;e.bindTexture(s.TEXTURE_CUBE_MAP,C.__webglTexture,s.TEXTURE0+X);let j=n.get(it);if(it.version!==j.__version||Q===!0){e.activeTexture(s.TEXTURE0+X);let xt=ge.getPrimaries(ge.workingColorSpace),pt=b.colorSpace===Us?null:ge.getPrimaries(b.colorSpace),bt=b.colorSpace===Us||xt===pt?s.NONE:s.BROWSER_DEFAULT_WEBGL;s.pixelStorei(s.UNPACK_FLIP_Y_WEBGL,b.flipY),s.pixelStorei(s.UNPACK_PREMULTIPLY_ALPHA_WEBGL,b.premultiplyAlpha),s.pixelStorei(s.UNPACK_ALIGNMENT,b.unpackAlignment),s.pixelStorei(s.UNPACK_COLORSPACE_CONVERSION_WEBGL,bt);let Kt=b.isCompressedTexture||b.image[0].isCompressedTexture,ut=b.image[0]&&b.image[0].isDataTexture,gt=[];for(let tt=0;tt<6;tt++)!Kt&&!ut?gt[tt]=_(b.image[tt],!0,i.maxCubemapSize):gt[tt]=ut?b.image[tt].image:b.image[tt],gt[tt]=zt(b,gt[tt]);let qt=gt[0],Yt=r.convert(b.format,b.colorSpace),Lt=r.convert(b.type),ee=y(b.internalFormat,Yt,Lt,b.colorSpace),Jt=b.isVideoTexture!==!0,Qt=j.__version===void 0||Q===!0,D=it.dataReady,yt=E(b,qt);Dt(s.TEXTURE_CUBE_MAP,b);let $;if(Kt){Jt&&Qt&&e.texStorage2D(s.TEXTURE_CUBE_MAP,yt,ee,qt.width,qt.height);for(let tt=0;tt<6;tt++){$=gt[tt].mipmaps;for(let Mt=0;Mt<$.length;Mt++){let wt=$[Mt];b.format!==bi?Yt!==null?Jt?D&&e.compressedTexSubImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+tt,Mt,0,0,wt.width,wt.height,Yt,wt.data):e.compressedTexImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+tt,Mt,ee,wt.width,wt.height,0,wt.data):console.warn("THREE.WebGLRenderer: Attempt to load unsupported compressed texture format in .setTextureCube()"):Jt?D&&e.texSubImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+tt,Mt,0,0,wt.width,wt.height,Yt,Lt,wt.data):e.texImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+tt,Mt,ee,wt.width,wt.height,0,Yt,Lt,wt.data)}}}else{if($=b.mipmaps,Jt&&Qt){$.length>0&&yt++;let tt=At(gt[0]);e.texStorage2D(s.TEXTURE_CUBE_MAP,yt,ee,tt.width,tt.height)}for(let tt=0;tt<6;tt++)if(ut){Jt?D&&e.texSubImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+tt,0,0,0,gt[tt].width,gt[tt].height,Yt,Lt,gt[tt].data):e.texImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+tt,0,ee,gt[tt].width,gt[tt].height,0,Yt,Lt,gt[tt].data);for(let Mt=0;Mt<$.length;Mt++){let K=$[Mt].image[tt].image;Jt?D&&e.texSubImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+tt,Mt+1,0,0,K.width,K.height,Yt,Lt,K.data):e.texImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+tt,Mt+1,ee,K.width,K.height,0,Yt,Lt,K.data)}}else{Jt?D&&e.texSubImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+tt,0,0,0,Yt,Lt,gt[tt]):e.texImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+tt,0,ee,Yt,Lt,gt[tt]);for(let Mt=0;Mt<$.length;Mt++){let wt=$[Mt];Jt?D&&e.texSubImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+tt,Mt+1,0,0,Yt,Lt,wt.image[tt]):e.texImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+tt,Mt+1,ee,Yt,Lt,wt.image[tt])}}}m(b)&&p(s.TEXTURE_CUBE_MAP),j.__version=it.version,b.onUpdate&&b.onUpdate(b)}C.__version=b.version}function St(C,b,X,Q,it,j){let xt=r.convert(X.format,X.colorSpace),pt=r.convert(X.type),bt=y(X.internalFormat,xt,pt,X.colorSpace),Kt=n.get(b),ut=n.get(X);if(ut.__renderTarget=b,!Kt.__hasExternalTextures){let gt=Math.max(1,b.width>>j),qt=Math.max(1,b.height>>j);it===s.TEXTURE_3D||it===s.TEXTURE_2D_ARRAY?e.texImage3D(it,j,bt,gt,qt,b.depth,0,xt,pt,null):e.texImage2D(it,j,bt,gt,qt,0,xt,pt,null)}e.bindFramebuffer(s.FRAMEBUFFER,C),O(b)?a.framebufferTexture2DMultisampleEXT(s.FRAMEBUFFER,Q,it,ut.__webglTexture,0,lt(b)):(it===s.TEXTURE_2D||it>=s.TEXTURE_CUBE_MAP_POSITIVE_X&&it<=s.TEXTURE_CUBE_MAP_NEGATIVE_Z)&&s.framebufferTexture2D(s.FRAMEBUFFER,Q,it,ut.__webglTexture,j),e.bindFramebuffer(s.FRAMEBUFFER,null)}function ot(C,b,X){if(s.bindRenderbuffer(s.RENDERBUFFER,C),b.depthBuffer){let Q=b.depthTexture,it=Q&&Q.isDepthTexture?Q.type:null,j=v(b.stencilBuffer,it),xt=b.stencilBuffer?s.DEPTH_STENCIL_ATTACHMENT:s.DEPTH_ATTACHMENT,pt=lt(b);O(b)?a.renderbufferStorageMultisampleEXT(s.RENDERBUFFER,pt,j,b.width,b.height):X?s.renderbufferStorageMultisample(s.RENDERBUFFER,pt,j,b.width,b.height):s.renderbufferStorage(s.RENDERBUFFER,j,b.width,b.height),s.framebufferRenderbuffer(s.FRAMEBUFFER,xt,s.RENDERBUFFER,C)}else{let Q=b.textures;for(let it=0;it<Q.length;it++){let j=Q[it],xt=r.convert(j.format,j.colorSpace),pt=r.convert(j.type),bt=y(j.internalFormat,xt,pt,j.colorSpace),Kt=lt(b);X&&O(b)===!1?s.renderbufferStorageMultisample(s.RENDERBUFFER,Kt,bt,b.width,b.height):O(b)?a.renderbufferStorageMultisampleEXT(s.RENDERBUFFER,Kt,bt,b.width,b.height):s.renderbufferStorage(s.RENDERBUFFER,bt,b.width,b.height)}}s.bindRenderbuffer(s.RENDERBUFFER,null)}function Rt(C,b){if(b&&b.isWebGLCubeRenderTarget)throw new Error("Depth Texture with cube render targets is not supported");if(e.bindFramebuffer(s.FRAMEBUFFER,C),!(b.depthTexture&&b.depthTexture.isDepthTexture))throw new Error("renderTarget.depthTexture must be an instance of THREE.DepthTexture");let Q=n.get(b.depthTexture);Q.__renderTarget=b,(!Q.__webglTexture||b.depthTexture.image.width!==b.width||b.depthTexture.image.height!==b.height)&&(b.depthTexture.image.width=b.width,b.depthTexture.image.height=b.height,b.depthTexture.needsUpdate=!0),q(b.depthTexture,0);let it=Q.__webglTexture,j=lt(b);if(b.depthTexture.format===Mo)O(b)?a.framebufferTexture2DMultisampleEXT(s.FRAMEBUFFER,s.DEPTH_ATTACHMENT,s.TEXTURE_2D,it,0,j):s.framebufferTexture2D(s.FRAMEBUFFER,s.DEPTH_ATTACHMENT,s.TEXTURE_2D,it,0);else if(b.depthTexture.format===Co)O(b)?a.framebufferTexture2DMultisampleEXT(s.FRAMEBUFFER,s.DEPTH_STENCIL_ATTACHMENT,s.TEXTURE_2D,it,0,j):s.framebufferTexture2D(s.FRAMEBUFFER,s.DEPTH_STENCIL_ATTACHMENT,s.TEXTURE_2D,it,0);else throw new Error("Unknown depthTexture format")}function Bt(C){let b=n.get(C),X=C.isWebGLCubeRenderTarget===!0;if(b.__boundDepthTexture!==C.depthTexture){let Q=C.depthTexture;if(b.__depthDisposeCallback&&b.__depthDisposeCallback(),Q){let it=()=>{delete b.__boundDepthTexture,delete b.__depthDisposeCallback,Q.removeEventListener("dispose",it)};Q.addEventListener("dispose",it),b.__depthDisposeCallback=it}b.__boundDepthTexture=Q}if(C.depthTexture&&!b.__autoAllocateDepthBuffer){if(X)throw new Error("target.depthTexture not supported in Cube render targets");Rt(b.__webglFramebuffer,C)}else if(X){b.__webglDepthbuffer=[];for(let Q=0;Q<6;Q++)if(e.bindFramebuffer(s.FRAMEBUFFER,b.__webglFramebuffer[Q]),b.__webglDepthbuffer[Q]===void 0)b.__webglDepthbuffer[Q]=s.createRenderbuffer(),ot(b.__webglDepthbuffer[Q],C,!1);else{let it=C.stencilBuffer?s.DEPTH_STENCIL_ATTACHMENT:s.DEPTH_ATTACHMENT,j=b.__webglDepthbuffer[Q];s.bindRenderbuffer(s.RENDERBUFFER,j),s.framebufferRenderbuffer(s.FRAMEBUFFER,it,s.RENDERBUFFER,j)}}else if(e.bindFramebuffer(s.FRAMEBUFFER,b.__webglFramebuffer),b.__webglDepthbuffer===void 0)b.__webglDepthbuffer=s.createRenderbuffer(),ot(b.__webglDepthbuffer,C,!1);else{let Q=C.stencilBuffer?s.DEPTH_STENCIL_ATTACHMENT:s.DEPTH_ATTACHMENT,it=b.__webglDepthbuffer;s.bindRenderbuffer(s.RENDERBUFFER,it),s.framebufferRenderbuffer(s.FRAMEBUFFER,Q,s.RENDERBUFFER,it)}e.bindFramebuffer(s.FRAMEBUFFER,null)}function Wt(C,b,X){let Q=n.get(C);b!==void 0&&St(Q.__webglFramebuffer,C,C.texture,s.COLOR_ATTACHMENT0,s.TEXTURE_2D,0),X!==void 0&&Bt(C)}function Xt(C){let b=C.texture,X=n.get(C),Q=n.get(b);C.addEventListener("dispose",T);let it=C.textures,j=C.isWebGLCubeRenderTarget===!0,xt=it.length>1;if(xt||(Q.__webglTexture===void 0&&(Q.__webglTexture=s.createTexture()),Q.__version=b.version,o.memory.textures++),j){X.__webglFramebuffer=[];for(let pt=0;pt<6;pt++)if(b.mipmaps&&b.mipmaps.length>0){X.__webglFramebuffer[pt]=[];for(let bt=0;bt<b.mipmaps.length;bt++)X.__webglFramebuffer[pt][bt]=s.createFramebuffer()}else X.__webglFramebuffer[pt]=s.createFramebuffer()}else{if(b.mipmaps&&b.mipmaps.length>0){X.__webglFramebuffer=[];for(let pt=0;pt<b.mipmaps.length;pt++)X.__webglFramebuffer[pt]=s.createFramebuffer()}else X.__webglFramebuffer=s.createFramebuffer();if(xt)for(let pt=0,bt=it.length;pt<bt;pt++){let Kt=n.get(it[pt]);Kt.__webglTexture===void 0&&(Kt.__webglTexture=s.createTexture(),o.memory.textures++)}if(C.samples>0&&O(C)===!1){X.__webglMultisampledFramebuffer=s.createFramebuffer(),X.__webglColorRenderbuffer=[],e.bindFramebuffer(s.FRAMEBUFFER,X.__webglMultisampledFramebuffer);for(let pt=0;pt<it.length;pt++){let bt=it[pt];X.__webglColorRenderbuffer[pt]=s.createRenderbuffer(),s.bindRenderbuffer(s.RENDERBUFFER,X.__webglColorRenderbuffer[pt]);let Kt=r.convert(bt.format,bt.colorSpace),ut=r.convert(bt.type),gt=y(bt.internalFormat,Kt,ut,bt.colorSpace,C.isXRRenderTarget===!0),qt=lt(C);s.renderbufferStorageMultisample(s.RENDERBUFFER,qt,gt,C.width,C.height),s.framebufferRenderbuffer(s.FRAMEBUFFER,s.COLOR_ATTACHMENT0+pt,s.RENDERBUFFER,X.__webglColorRenderbuffer[pt])}s.bindRenderbuffer(s.RENDERBUFFER,null),C.depthBuffer&&(X.__webglDepthRenderbuffer=s.createRenderbuffer(),ot(X.__webglDepthRenderbuffer,C,!0)),e.bindFramebuffer(s.FRAMEBUFFER,null)}}if(j){e.bindTexture(s.TEXTURE_CUBE_MAP,Q.__webglTexture),Dt(s.TEXTURE_CUBE_MAP,b);for(let pt=0;pt<6;pt++)if(b.mipmaps&&b.mipmaps.length>0)for(let bt=0;bt<b.mipmaps.length;bt++)St(X.__webglFramebuffer[pt][bt],C,b,s.COLOR_ATTACHMENT0,s.TEXTURE_CUBE_MAP_POSITIVE_X+pt,bt);else St(X.__webglFramebuffer[pt],C,b,s.COLOR_ATTACHMENT0,s.TEXTURE_CUBE_MAP_POSITIVE_X+pt,0);m(b)&&p(s.TEXTURE_CUBE_MAP),e.unbindTexture()}else if(xt){for(let pt=0,bt=it.length;pt<bt;pt++){let Kt=it[pt],ut=n.get(Kt);e.bindTexture(s.TEXTURE_2D,ut.__webglTexture),Dt(s.TEXTURE_2D,Kt),St(X.__webglFramebuffer,C,Kt,s.COLOR_ATTACHMENT0+pt,s.TEXTURE_2D,0),m(Kt)&&p(s.TEXTURE_2D)}e.unbindTexture()}else{let pt=s.TEXTURE_2D;if((C.isWebGL3DRenderTarget||C.isWebGLArrayRenderTarget)&&(pt=C.isWebGL3DRenderTarget?s.TEXTURE_3D:s.TEXTURE_2D_ARRAY),e.bindTexture(pt,Q.__webglTexture),Dt(pt,b),b.mipmaps&&b.mipmaps.length>0)for(let bt=0;bt<b.mipmaps.length;bt++)St(X.__webglFramebuffer[bt],C,b,s.COLOR_ATTACHMENT0,pt,bt);else St(X.__webglFramebuffer,C,b,s.COLOR_ATTACHMENT0,pt,0);m(b)&&p(pt),e.unbindTexture()}C.depthBuffer&&Bt(C)}function et(C){let b=C.textures;for(let X=0,Q=b.length;X<Q;X++){let it=b[X];if(m(it)){let j=S(C),xt=n.get(it).__webglTexture;e.bindTexture(j,xt),p(j),e.unbindTexture()}}}let nt=[],P=[];function It(C){if(C.samples>0){if(O(C)===!1){let b=C.textures,X=C.width,Q=C.height,it=s.COLOR_BUFFER_BIT,j=C.stencilBuffer?s.DEPTH_STENCIL_ATTACHMENT:s.DEPTH_ATTACHMENT,xt=n.get(C),pt=b.length>1;if(pt)for(let bt=0;bt<b.length;bt++)e.bindFramebuffer(s.FRAMEBUFFER,xt.__webglMultisampledFramebuffer),s.framebufferRenderbuffer(s.FRAMEBUFFER,s.COLOR_ATTACHMENT0+bt,s.RENDERBUFFER,null),e.bindFramebuffer(s.FRAMEBUFFER,xt.__webglFramebuffer),s.framebufferTexture2D(s.DRAW_FRAMEBUFFER,s.COLOR_ATTACHMENT0+bt,s.TEXTURE_2D,null,0);e.bindFramebuffer(s.READ_FRAMEBUFFER,xt.__webglMultisampledFramebuffer),e.bindFramebuffer(s.DRAW_FRAMEBUFFER,xt.__webglFramebuffer);for(let bt=0;bt<b.length;bt++){if(C.resolveDepthBuffer&&(C.depthBuffer&&(it|=s.DEPTH_BUFFER_BIT),C.stencilBuffer&&C.resolveStencilBuffer&&(it|=s.STENCIL_BUFFER_BIT)),pt){s.framebufferRenderbuffer(s.READ_FRAMEBUFFER,s.COLOR_ATTACHMENT0,s.RENDERBUFFER,xt.__webglColorRenderbuffer[bt]);let Kt=n.get(b[bt]).__webglTexture;s.framebufferTexture2D(s.DRAW_FRAMEBUFFER,s.COLOR_ATTACHMENT0,s.TEXTURE_2D,Kt,0)}s.blitFramebuffer(0,0,X,Q,0,0,X,Q,it,s.NEAREST),l===!0&&(nt.length=0,P.length=0,nt.push(s.COLOR_ATTACHMENT0+bt),C.depthBuffer&&C.resolveDepthBuffer===!1&&(nt.push(j),P.push(j),s.invalidateFramebuffer(s.DRAW_FRAMEBUFFER,P)),s.invalidateFramebuffer(s.READ_FRAMEBUFFER,nt))}if(e.bindFramebuffer(s.READ_FRAMEBUFFER,null),e.bindFramebuffer(s.DRAW_FRAMEBUFFER,null),pt)for(let bt=0;bt<b.length;bt++){e.bindFramebuffer(s.FRAMEBUFFER,xt.__webglMultisampledFramebuffer),s.framebufferRenderbuffer(s.FRAMEBUFFER,s.COLOR_ATTACHMENT0+bt,s.RENDERBUFFER,xt.__webglColorRenderbuffer[bt]);let Kt=n.get(b[bt]).__webglTexture;e.bindFramebuffer(s.FRAMEBUFFER,xt.__webglFramebuffer),s.framebufferTexture2D(s.DRAW_FRAMEBUFFER,s.COLOR_ATTACHMENT0+bt,s.TEXTURE_2D,Kt,0)}e.bindFramebuffer(s.DRAW_FRAMEBUFFER,xt.__webglMultisampledFramebuffer)}else if(C.depthBuffer&&C.resolveDepthBuffer===!1&&l){let b=C.stencilBuffer?s.DEPTH_STENCIL_ATTACHMENT:s.DEPTH_ATTACHMENT;s.invalidateFramebuffer(s.DRAW_FRAMEBUFFER,[b])}}}function lt(C){return Math.min(i.maxSamples,C.samples)}function O(C){let b=n.get(C);return C.samples>0&&t.has("WEBGL_multisampled_render_to_texture")===!0&&b.__useRenderToTexture!==!1}function dt(C){let b=o.render.frame;h.get(C)!==b&&(h.set(C,b),C.update())}function zt(C,b){let X=C.colorSpace,Q=C.format,it=C.type;return C.isCompressedTexture===!0||C.isVideoTexture===!0||X!==Oo&&X!==Us&&(ge.getTransfer(X)===we?(Q!==bi||it!==os)&&console.warn("THREE.WebGLTextures: sRGB encoded textures have to use RGBAFormat and UnsignedByteType."):console.error("THREE.WebGLTextures: Unsupported texture color space:",X)),b}function At(C){return typeof HTMLImageElement<"u"&&C instanceof HTMLImageElement?(c.width=C.naturalWidth||C.width,c.height=C.naturalHeight||C.height):typeof VideoFrame<"u"&&C instanceof VideoFrame?(c.width=C.displayWidth,c.height=C.displayHeight):(c.width=C.width,c.height=C.height),c}this.allocateTextureUnit=F,this.resetTextureUnits=U,this.setTexture2D=q,this.setTexture2DArray=H,this.setTexture3D=W,this.setTextureCube=V,this.rebindTextures=Wt,this.setupRenderTarget=Xt,this.updateRenderTargetMipmap=et,this.updateMultisampleRenderTarget=It,this.setupDepthRenderbuffer=Bt,this.setupFrameBufferTexture=St,this.useMultisampledRTT=O}function nw(s,t){function e(n,i=Us){let r,o=ge.getTransfer(i);if(n===os)return s.UNSIGNED_BYTE;if(n===kd)return s.UNSIGNED_SHORT_4_4_4_4;if(n===zd)return s.UNSIGNED_SHORT_5_5_5_1;if(n===D_)return s.UNSIGNED_INT_5_9_9_9_REV;if(n===I_)return s.BYTE;if(n===L_)return s.SHORT;if(n===za)return s.UNSIGNED_SHORT;if(n===Bd)return s.INT;if(n===Mr)return s.UNSIGNED_INT;if(n===Bi)return s.FLOAT;if(n===ei)return s.HALF_FLOAT;if(n===U_)return s.ALPHA;if(n===N_)return s.RGB;if(n===bi)return s.RGBA;if(n===O_)return s.LUMINANCE;if(n===F_)return s.LUMINANCE_ALPHA;if(n===Mo)return s.DEPTH_COMPONENT;if(n===Co)return s.DEPTH_STENCIL;if(n===Vd)return s.RED;if(n===Hd)return s.RED_INTEGER;if(n===B_)return s.RG;if(n===Gd)return s.RG_INTEGER;if(n===Wd)return s.RGBA_INTEGER;if(n===gc||n===_c||n===vc||n===xc)if(o===we)if(r=t.get("WEBGL_compressed_texture_s3tc_srgb"),r!==null){if(n===gc)return r.COMPRESSED_SRGB_S3TC_DXT1_EXT;if(n===_c)return r.COMPRESSED_SRGB_ALPHA_S3TC_DXT1_EXT;if(n===vc)return r.COMPRESSED_SRGB_ALPHA_S3TC_DXT3_EXT;if(n===xc)return r.COMPRESSED_SRGB_ALPHA_S3TC_DXT5_EXT}else return null;else if(r=t.get("WEBGL_compressed_texture_s3tc"),r!==null){if(n===gc)return r.COMPRESSED_RGB_S3TC_DXT1_EXT;if(n===_c)return r.COMPRESSED_RGBA_S3TC_DXT1_EXT;if(n===vc)return r.COMPRESSED_RGBA_S3TC_DXT3_EXT;if(n===xc)return r.COMPRESSED_RGBA_S3TC_DXT5_EXT}else return null;if(n===yf||n===Mf||n===Sf||n===bf)if(r=t.get("WEBGL_compressed_texture_pvrtc"),r!==null){if(n===yf)return r.COMPRESSED_RGB_PVRTC_4BPPV1_IMG;if(n===Mf)return r.COMPRESSED_RGB_PVRTC_2BPPV1_IMG;if(n===Sf)return r.COMPRESSED_RGBA_PVRTC_4BPPV1_IMG;if(n===bf)return r.COMPRESSED_RGBA_PVRTC_2BPPV1_IMG}else return null;if(n===wf||n===Tf||n===Ef)if(r=t.get("WEBGL_compressed_texture_etc"),r!==null){if(n===wf||n===Tf)return o===we?r.COMPRESSED_SRGB8_ETC2:r.COMPRESSED_RGB8_ETC2;if(n===Ef)return o===we?r.COMPRESSED_SRGB8_ALPHA8_ETC2_EAC:r.COMPRESSED_RGBA8_ETC2_EAC}else return null;if(n===Af||n===Cf||n===Rf||n===Pf||n===If||n===Lf||n===Df||n===Uf||n===Nf||n===Of||n===Ff||n===Bf||n===kf||n===zf)if(r=t.get("WEBGL_compressed_texture_astc"),r!==null){if(n===Af)return o===we?r.COMPRESSED_SRGB8_ALPHA8_ASTC_4x4_KHR:r.COMPRESSED_RGBA_ASTC_4x4_KHR;if(n===Cf)return o===we?r.COMPRESSED_SRGB8_ALPHA8_ASTC_5x4_KHR:r.COMPRESSED_RGBA_ASTC_5x4_KHR;if(n===Rf)return o===we?r.COMPRESSED_SRGB8_ALPHA8_ASTC_5x5_KHR:r.COMPRESSED_RGBA_ASTC_5x5_KHR;if(n===Pf)return o===we?r.COMPRESSED_SRGB8_ALPHA8_ASTC_6x5_KHR:r.COMPRESSED_RGBA_ASTC_6x5_KHR;if(n===If)return o===we?r.COMPRESSED_SRGB8_ALPHA8_ASTC_6x6_KHR:r.COMPRESSED_RGBA_ASTC_6x6_KHR;if(n===Lf)return o===we?r.COMPRESSED_SRGB8_ALPHA8_ASTC_8x5_KHR:r.COMPRESSED_RGBA_ASTC_8x5_KHR;if(n===Df)return o===we?r.COMPRESSED_SRGB8_ALPHA8_ASTC_8x6_KHR:r.COMPRESSED_RGBA_ASTC_8x6_KHR;if(n===Uf)return o===we?r.COMPRESSED_SRGB8_ALPHA8_ASTC_8x8_KHR:r.COMPRESSED_RGBA_ASTC_8x8_KHR;if(n===Nf)return o===we?r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x5_KHR:r.COMPRESSED_RGBA_ASTC_10x5_KHR;if(n===Of)return o===we?r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x6_KHR:r.COMPRESSED_RGBA_ASTC_10x6_KHR;if(n===Ff)return o===we?r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x8_KHR:r.COMPRESSED_RGBA_ASTC_10x8_KHR;if(n===Bf)return o===we?r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x10_KHR:r.COMPRESSED_RGBA_ASTC_10x10_KHR;if(n===kf)return o===we?r.COMPRESSED_SRGB8_ALPHA8_ASTC_12x10_KHR:r.COMPRESSED_RGBA_ASTC_12x10_KHR;if(n===zf)return o===we?r.COMPRESSED_SRGB8_ALPHA8_ASTC_12x12_KHR:r.COMPRESSED_RGBA_ASTC_12x12_KHR}else return null;if(n===yc||n===Vf||n===Hf)if(r=t.get("EXT_texture_compression_bptc"),r!==null){if(n===yc)return o===we?r.COMPRESSED_SRGB_ALPHA_BPTC_UNORM_EXT:r.COMPRESSED_RGBA_BPTC_UNORM_EXT;if(n===Vf)return r.COMPRESSED_RGB_BPTC_SIGNED_FLOAT_EXT;if(n===Hf)return r.COMPRESSED_RGB_BPTC_UNSIGNED_FLOAT_EXT}else return null;if(n===k_||n===Gf||n===Wf||n===Xf)if(r=t.get("EXT_texture_compression_rgtc"),r!==null){if(n===yc)return r.COMPRESSED_RED_RGTC1_EXT;if(n===Gf)return r.COMPRESSED_SIGNED_RED_RGTC1_EXT;if(n===Wf)return r.COMPRESSED_RED_GREEN_RGTC2_EXT;if(n===Xf)return r.COMPRESSED_SIGNED_RED_GREEN_RGTC2_EXT}else return null;return n===Ao?s.UNSIGNED_INT_24_8:s[n]!==void 0?s[n]:null}return{convert:e}}var ld=class extends bn{constructor(t=[]){super(),this.isArrayCamera=!0,this.cameras=t}},Ns=class extends Hn{constructor(){super(),this.isGroup=!0,this.type="Group"}},iw={type:"move"},Fa=class{constructor(){this._targetRay=null,this._grip=null,this._hand=null}getHandSpace(){return this._hand===null&&(this._hand=new Ns,this._hand.matrixAutoUpdate=!1,this._hand.visible=!1,this._hand.joints={},this._hand.inputState={pinching:!1}),this._hand}getTargetRaySpace(){return this._targetRay===null&&(this._targetRay=new Ns,this._targetRay.matrixAutoUpdate=!1,this._targetRay.visible=!1,this._targetRay.hasLinearVelocity=!1,this._targetRay.linearVelocity=new B,this._targetRay.hasAngularVelocity=!1,this._targetRay.angularVelocity=new B),this._targetRay}getGripSpace(){return this._grip===null&&(this._grip=new Ns,this._grip.matrixAutoUpdate=!1,this._grip.visible=!1,this._grip.hasLinearVelocity=!1,this._grip.linearVelocity=new B,this._grip.hasAngularVelocity=!1,this._grip.angularVelocity=new B),this._grip}dispatchEvent(t){return this._targetRay!==null&&this._targetRay.dispatchEvent(t),this._grip!==null&&this._grip.dispatchEvent(t),this._hand!==null&&this._hand.dispatchEvent(t),this}connect(t){if(t&&t.hand){let e=this._hand;if(e)for(let n of t.hand.values())this._getHandJoint(e,n)}return this.dispatchEvent({type:"connected",data:t}),this}disconnect(t){return this.dispatchEvent({type:"disconnected",data:t}),this._targetRay!==null&&(this._targetRay.visible=!1),this._grip!==null&&(this._grip.visible=!1),this._hand!==null&&(this._hand.visible=!1),this}update(t,e,n){let i=null,r=null,o=null,a=this._targetRay,l=this._grip,c=this._hand;if(t&&e.session.visibilityState!=="visible-blurred"){if(c&&t.hand){o=!0;for(let _ of t.hand.values()){let m=e.getJointPose(_,n),p=this._getHandJoint(c,_);m!==null&&(p.matrix.fromArray(m.transform.matrix),p.matrix.decompose(p.position,p.rotation,p.scale),p.matrixWorldNeedsUpdate=!0,p.jointRadius=m.radius),p.visible=m!==null}let h=c.joints["index-finger-tip"],u=c.joints["thumb-tip"],f=h.position.distanceTo(u.position),d=.02,g=.005;c.inputState.pinching&&f>d+g?(c.inputState.pinching=!1,this.dispatchEvent({type:"pinchend",handedness:t.handedness,target:this})):!c.inputState.pinching&&f<=d-g&&(c.inputState.pinching=!0,this.dispatchEvent({type:"pinchstart",handedness:t.handedness,target:this}))}else l!==null&&t.gripSpace&&(r=e.getPose(t.gripSpace,n),r!==null&&(l.matrix.fromArray(r.transform.matrix),l.matrix.decompose(l.position,l.rotation,l.scale),l.matrixWorldNeedsUpdate=!0,r.linearVelocity?(l.hasLinearVelocity=!0,l.linearVelocity.copy(r.linearVelocity)):l.hasLinearVelocity=!1,r.angularVelocity?(l.hasAngularVelocity=!0,l.angularVelocity.copy(r.angularVelocity)):l.hasAngularVelocity=!1));a!==null&&(i=e.getPose(t.targetRaySpace,n),i===null&&r!==null&&(i=r),i!==null&&(a.matrix.fromArray(i.transform.matrix),a.matrix.decompose(a.position,a.rotation,a.scale),a.matrixWorldNeedsUpdate=!0,i.linearVelocity?(a.hasLinearVelocity=!0,a.linearVelocity.copy(i.linearVelocity)):a.hasLinearVelocity=!1,i.angularVelocity?(a.hasAngularVelocity=!0,a.angularVelocity.copy(i.angularVelocity)):a.hasAngularVelocity=!1,this.dispatchEvent(iw)))}return a!==null&&(a.visible=i!==null),l!==null&&(l.visible=r!==null),c!==null&&(c.visible=o!==null),this}_getHandJoint(t,e){if(t.joints[e.jointName]===void 0){let n=new Ns;n.matrixAutoUpdate=!1,n.visible=!1,t.joints[e.jointName]=n,t.add(n)}return t.joints[e.jointName]}},sw=`
void main() {

	gl_Position = vec4( position, 1.0 );

}`,rw=`
uniform sampler2DArray depthColor;
uniform float depthWidth;
uniform float depthHeight;

void main() {

	vec2 coord = vec2( gl_FragCoord.x / depthWidth, gl_FragCoord.y / depthHeight );

	if ( coord.x >= 1.0 ) {

		gl_FragDepth = texture( depthColor, vec3( coord.x - 1.0, coord.y, 1 ) ).r;

	} else {

		gl_FragDepth = texture( depthColor, vec3( coord.x, coord.y, 0 ) ).r;

	}

}`,cd=class{constructor(){this.texture=null,this.mesh=null,this.depthNear=0,this.depthFar=0}init(t,e,n){if(this.texture===null){let i=new Vn,r=t.properties.get(i);r.__webglTexture=e.texture,(e.depthNear!=n.depthNear||e.depthFar!=n.depthFar)&&(this.depthNear=e.depthNear,this.depthFar=e.depthFar),this.texture=i}}getMesh(t){if(this.texture!==null&&this.mesh===null){let e=t.cameras[0].viewport,n=new je({vertexShader:sw,fragmentShader:rw,uniforms:{depthColor:{value:this.texture},depthWidth:{value:e.z},depthHeight:{value:e.w}}});this.mesh=new ve(new Tr(20,20),n)}return this.mesh}reset(){this.texture=null,this.mesh=null}getDepthTexture(){return this.texture}},hd=class extends ks{constructor(t,e){super();let n=this,i=null,r=1,o=null,a="local-floor",l=1,c=null,h=null,u=null,f=null,d=null,g=null,_=new cd,m=e.getContextAttributes(),p=null,S=null,y=[],v=[],E=new vt,A=null,T=new bn;T.viewport=new Ae;let R=new bn;R.viewport=new Ae;let M=[T,R],x=new ld,L=null,U=null;this.cameraAutoUpdate=!0,this.enabled=!1,this.isPresenting=!1,this.getController=function(Z){let rt=y[Z];return rt===void 0&&(rt=new Fa,y[Z]=rt),rt.getTargetRaySpace()},this.getControllerGrip=function(Z){let rt=y[Z];return rt===void 0&&(rt=new Fa,y[Z]=rt),rt.getGripSpace()},this.getHand=function(Z){let rt=y[Z];return rt===void 0&&(rt=new Fa,y[Z]=rt),rt.getHandSpace()};function F(Z){let rt=v.indexOf(Z.inputSource);if(rt===-1)return;let St=y[rt];St!==void 0&&(St.update(Z.inputSource,Z.frame,c||o),St.dispatchEvent({type:Z.type,data:Z.inputSource}))}function z(){i.removeEventListener("select",F),i.removeEventListener("selectstart",F),i.removeEventListener("selectend",F),i.removeEventListener("squeeze",F),i.removeEventListener("squeezestart",F),i.removeEventListener("squeezeend",F),i.removeEventListener("end",z),i.removeEventListener("inputsourceschange",q);for(let Z=0;Z<y.length;Z++){let rt=v[Z];rt!==null&&(v[Z]=null,y[Z].disconnect(rt))}L=null,U=null,_.reset(),t.setRenderTarget(p),d=null,f=null,u=null,i=null,S=null,Vt.stop(),n.isPresenting=!1,t.setPixelRatio(A),t.setSize(E.width,E.height,!1),n.dispatchEvent({type:"sessionend"})}this.setFramebufferScaleFactor=function(Z){r=Z,n.isPresenting===!0&&console.warn("THREE.WebXRManager: Cannot change framebuffer scale while presenting.")},this.setReferenceSpaceType=function(Z){a=Z,n.isPresenting===!0&&console.warn("THREE.WebXRManager: Cannot change reference space type while presenting.")},this.getReferenceSpace=function(){return c||o},this.setReferenceSpace=function(Z){c=Z},this.getBaseLayer=function(){return f!==null?f:d},this.getBinding=function(){return u},this.getFrame=function(){return g},this.getSession=function(){return i},this.setSession=async function(Z){if(i=Z,i!==null){if(p=t.getRenderTarget(),i.addEventListener("select",F),i.addEventListener("selectstart",F),i.addEventListener("selectend",F),i.addEventListener("squeeze",F),i.addEventListener("squeezestart",F),i.addEventListener("squeezeend",F),i.addEventListener("end",z),i.addEventListener("inputsourceschange",q),m.xrCompatible!==!0&&await e.makeXRCompatible(),A=t.getPixelRatio(),t.getSize(E),i.renderState.layers===void 0){let rt={antialias:m.antialias,alpha:!0,depth:m.depth,stencil:m.stencil,framebufferScaleFactor:r};d=new XRWebGLLayer(i,e,rt),i.updateRenderState({baseLayer:d}),t.setPixelRatio(1),t.setSize(d.framebufferWidth,d.framebufferHeight,!1),S=new un(d.framebufferWidth,d.framebufferHeight,{format:bi,type:os,colorSpace:t.outputColorSpace,stencilBuffer:m.stencil})}else{let rt=null,St=null,ot=null;m.depth&&(ot=m.stencil?e.DEPTH24_STENCIL8:e.DEPTH_COMPONENT24,rt=m.stencil?Co:Mo,St=m.stencil?Ao:Mr);let Rt={colorFormat:e.RGBA8,depthFormat:ot,scaleFactor:r};u=new XRWebGLBinding(i,e),f=u.createProjectionLayer(Rt),i.updateRenderState({layers:[f]}),t.setPixelRatio(1),t.setSize(f.textureWidth,f.textureHeight,!1),S=new un(f.textureWidth,f.textureHeight,{format:bi,type:os,depthTexture:new Lc(f.textureWidth,f.textureHeight,St,void 0,void 0,void 0,void 0,void 0,void 0,rt),stencilBuffer:m.stencil,colorSpace:t.outputColorSpace,samples:m.antialias?4:0,resolveDepthBuffer:f.ignoreDepthValues===!1})}S.isXRRenderTarget=!0,this.setFoveation(l),c=null,o=await i.requestReferenceSpace(a),Vt.setContext(i),Vt.start(),n.isPresenting=!0,n.dispatchEvent({type:"sessionstart"})}},this.getEnvironmentBlendMode=function(){if(i!==null)return i.environmentBlendMode},this.getDepthTexture=function(){return _.getDepthTexture()};function q(Z){for(let rt=0;rt<Z.removed.length;rt++){let St=Z.removed[rt],ot=v.indexOf(St);ot>=0&&(v[ot]=null,y[ot].disconnect(St))}for(let rt=0;rt<Z.added.length;rt++){let St=Z.added[rt],ot=v.indexOf(St);if(ot===-1){for(let Bt=0;Bt<y.length;Bt++)if(Bt>=v.length){v.push(St),ot=Bt;break}else if(v[Bt]===null){v[Bt]=St,ot=Bt;break}if(ot===-1)break}let Rt=y[ot];Rt&&Rt.connect(St)}}let H=new B,W=new B;function V(Z,rt,St){H.setFromMatrixPosition(rt.matrixWorld),W.setFromMatrixPosition(St.matrixWorld);let ot=H.distanceTo(W),Rt=rt.projectionMatrix.elements,Bt=St.projectionMatrix.elements,Wt=Rt[14]/(Rt[10]-1),Xt=Rt[14]/(Rt[10]+1),et=(Rt[9]+1)/Rt[5],nt=(Rt[9]-1)/Rt[5],P=(Rt[8]-1)/Rt[0],It=(Bt[8]+1)/Bt[0],lt=Wt*P,O=Wt*It,dt=ot/(-P+It),zt=dt*-P;if(rt.matrixWorld.decompose(Z.position,Z.quaternion,Z.scale),Z.translateX(zt),Z.translateZ(dt),Z.matrixWorld.compose(Z.position,Z.quaternion,Z.scale),Z.matrixWorldInverse.copy(Z.matrixWorld).invert(),Rt[10]===-1)Z.projectionMatrix.copy(rt.projectionMatrix),Z.projectionMatrixInverse.copy(rt.projectionMatrixInverse);else{let At=Wt+dt,C=Xt+dt,b=lt-zt,X=O+(ot-zt),Q=et*Xt/C*At,it=nt*Xt/C*At;Z.projectionMatrix.makePerspective(b,X,Q,it,At,C),Z.projectionMatrixInverse.copy(Z.projectionMatrix).invert()}}function st(Z,rt){rt===null?Z.matrixWorld.copy(Z.matrix):Z.matrixWorld.multiplyMatrices(rt.matrixWorld,Z.matrix),Z.matrixWorldInverse.copy(Z.matrixWorld).invert()}this.updateCamera=function(Z){if(i===null)return;let rt=Z.near,St=Z.far;_.texture!==null&&(_.depthNear>0&&(rt=_.depthNear),_.depthFar>0&&(St=_.depthFar)),x.near=R.near=T.near=rt,x.far=R.far=T.far=St,(L!==x.near||U!==x.far)&&(i.updateRenderState({depthNear:x.near,depthFar:x.far}),L=x.near,U=x.far),T.layers.mask=Z.layers.mask|2,R.layers.mask=Z.layers.mask|4,x.layers.mask=T.layers.mask|R.layers.mask;let ot=Z.parent,Rt=x.cameras;st(x,ot);for(let Bt=0;Bt<Rt.length;Bt++)st(Rt[Bt],ot);Rt.length===2?V(x,T,R):x.projectionMatrix.copy(T.projectionMatrix),I(Z,x,ot)};function I(Z,rt,St){St===null?Z.matrix.copy(rt.matrixWorld):(Z.matrix.copy(St.matrixWorld),Z.matrix.invert(),Z.matrix.multiply(rt.matrixWorld)),Z.matrix.decompose(Z.position,Z.quaternion,Z.scale),Z.updateMatrixWorld(!0),Z.projectionMatrix.copy(rt.projectionMatrix),Z.projectionMatrixInverse.copy(rt.projectionMatrixInverse),Z.isPerspectiveCamera&&(Z.fov=qf*2*Math.atan(1/Z.projectionMatrix.elements[5]),Z.zoom=1)}this.getCamera=function(){return x},this.getFoveation=function(){if(!(f===null&&d===null))return l},this.setFoveation=function(Z){l=Z,f!==null&&(f.fixedFoveation=Z),d!==null&&d.fixedFoveation!==void 0&&(d.fixedFoveation=Z)},this.hasDepthSensing=function(){return _.texture!==null},this.getDepthSensingMesh=function(){return _.getMesh(x)};let at=null;function Dt(Z,rt){if(h=rt.getViewerPose(c||o),g=rt,h!==null){let St=h.views;d!==null&&(t.setRenderTargetFramebuffer(S,d.framebuffer),t.setRenderTarget(S));let ot=!1;St.length!==x.cameras.length&&(x.cameras.length=0,ot=!0);for(let Bt=0;Bt<St.length;Bt++){let Wt=St[Bt],Xt=null;if(d!==null)Xt=d.getViewport(Wt);else{let nt=u.getViewSubImage(f,Wt);Xt=nt.viewport,Bt===0&&(t.setRenderTargetTextures(S,nt.colorTexture,f.ignoreDepthValues?void 0:nt.depthStencilTexture),t.setRenderTarget(S))}let et=M[Bt];et===void 0&&(et=new bn,et.layers.enable(Bt),et.viewport=new Ae,M[Bt]=et),et.matrix.fromArray(Wt.transform.matrix),et.matrix.decompose(et.position,et.quaternion,et.scale),et.projectionMatrix.fromArray(Wt.projectionMatrix),et.projectionMatrixInverse.copy(et.projectionMatrix).invert(),et.viewport.set(Xt.x,Xt.y,Xt.width,Xt.height),Bt===0&&(x.matrix.copy(et.matrix),x.matrix.decompose(x.position,x.quaternion,x.scale)),ot===!0&&x.cameras.push(et)}let Rt=i.enabledFeatures;if(Rt&&Rt.includes("depth-sensing")){let Bt=u.getDepthInformation(St[0]);Bt&&Bt.isValid&&Bt.texture&&_.init(t,Bt,i.renderState)}}for(let St=0;St<y.length;St++){let ot=v[St],Rt=y[St];ot!==null&&Rt!==void 0&&Rt.update(ot,rt,c||o)}at&&at(Z,rt),rt.detectedPlanes&&n.dispatchEvent({type:"planesdetected",data:rt}),g=null}let Vt=new X_;Vt.setAnimationLoop(Dt),this.setAnimationLoop=function(Z){at=Z},this.dispose=function(){}}},pr=new mi,ow=new Ce;function aw(s,t){function e(m,p){m.matrixAutoUpdate===!0&&m.updateMatrix(),p.value.copy(m.matrix)}function n(m,p){p.color.getRGB(m.fogColor.value,W_(s)),p.isFog?(m.fogNear.value=p.near,m.fogFar.value=p.far):p.isFogExp2&&(m.fogDensity.value=p.density)}function i(m,p,S,y,v){p.isMeshBasicMaterial||p.isMeshLambertMaterial?r(m,p):p.isMeshToonMaterial?(r(m,p),u(m,p)):p.isMeshPhongMaterial?(r(m,p),h(m,p)):p.isMeshStandardMaterial?(r(m,p),f(m,p),p.isMeshPhysicalMaterial&&d(m,p,v)):p.isMeshMatcapMaterial?(r(m,p),g(m,p)):p.isMeshDepthMaterial?r(m,p):p.isMeshDistanceMaterial?(r(m,p),_(m,p)):p.isMeshNormalMaterial?r(m,p):p.isLineBasicMaterial?(o(m,p),p.isLineDashedMaterial&&a(m,p)):p.isPointsMaterial?l(m,p,S,y):p.isSpriteMaterial?c(m,p):p.isShadowMaterial?(m.color.value.copy(p.color),m.opacity.value=p.opacity):p.isShaderMaterial&&(p.uniformsNeedUpdate=!1)}function r(m,p){m.opacity.value=p.opacity,p.color&&m.diffuse.value.copy(p.color),p.emissive&&m.emissive.value.copy(p.emissive).multiplyScalar(p.emissiveIntensity),p.map&&(m.map.value=p.map,e(p.map,m.mapTransform)),p.alphaMap&&(m.alphaMap.value=p.alphaMap,e(p.alphaMap,m.alphaMapTransform)),p.bumpMap&&(m.bumpMap.value=p.bumpMap,e(p.bumpMap,m.bumpMapTransform),m.bumpScale.value=p.bumpScale,p.side===wn&&(m.bumpScale.value*=-1)),p.normalMap&&(m.normalMap.value=p.normalMap,e(p.normalMap,m.normalMapTransform),m.normalScale.value.copy(p.normalScale),p.side===wn&&m.normalScale.value.negate()),p.displacementMap&&(m.displacementMap.value=p.displacementMap,e(p.displacementMap,m.displacementMapTransform),m.displacementScale.value=p.displacementScale,m.displacementBias.value=p.displacementBias),p.emissiveMap&&(m.emissiveMap.value=p.emissiveMap,e(p.emissiveMap,m.emissiveMapTransform)),p.specularMap&&(m.specularMap.value=p.specularMap,e(p.specularMap,m.specularMapTransform)),p.alphaTest>0&&(m.alphaTest.value=p.alphaTest);let S=t.get(p),y=S.envMap,v=S.envMapRotation;y&&(m.envMap.value=y,pr.copy(v),pr.x*=-1,pr.y*=-1,pr.z*=-1,y.isCubeTexture&&y.isRenderTargetTexture===!1&&(pr.y*=-1,pr.z*=-1),m.envMapRotation.value.setFromMatrix4(ow.makeRotationFromEuler(pr)),m.flipEnvMap.value=y.isCubeTexture&&y.isRenderTargetTexture===!1?-1:1,m.reflectivity.value=p.reflectivity,m.ior.value=p.ior,m.refractionRatio.value=p.refractionRatio),p.lightMap&&(m.lightMap.value=p.lightMap,m.lightMapIntensity.value=p.lightMapIntensity,e(p.lightMap,m.lightMapTransform)),p.aoMap&&(m.aoMap.value=p.aoMap,m.aoMapIntensity.value=p.aoMapIntensity,e(p.aoMap,m.aoMapTransform))}function o(m,p){m.diffuse.value.copy(p.color),m.opacity.value=p.opacity,p.map&&(m.map.value=p.map,e(p.map,m.mapTransform))}function a(m,p){m.dashSize.value=p.dashSize,m.totalSize.value=p.dashSize+p.gapSize,m.scale.value=p.scale}function l(m,p,S,y){m.diffuse.value.copy(p.color),m.opacity.value=p.opacity,m.size.value=p.size*S,m.scale.value=y*.5,p.map&&(m.map.value=p.map,e(p.map,m.uvTransform)),p.alphaMap&&(m.alphaMap.value=p.alphaMap,e(p.alphaMap,m.alphaMapTransform)),p.alphaTest>0&&(m.alphaTest.value=p.alphaTest)}function c(m,p){m.diffuse.value.copy(p.color),m.opacity.value=p.opacity,m.rotation.value=p.rotation,p.map&&(m.map.value=p.map,e(p.map,m.mapTransform)),p.alphaMap&&(m.alphaMap.value=p.alphaMap,e(p.alphaMap,m.alphaMapTransform)),p.alphaTest>0&&(m.alphaTest.value=p.alphaTest)}function h(m,p){m.specular.value.copy(p.specular),m.shininess.value=Math.max(p.shininess,1e-4)}function u(m,p){p.gradientMap&&(m.gradientMap.value=p.gradientMap)}function f(m,p){m.metalness.value=p.metalness,p.metalnessMap&&(m.metalnessMap.value=p.metalnessMap,e(p.metalnessMap,m.metalnessMapTransform)),m.roughness.value=p.roughness,p.roughnessMap&&(m.roughnessMap.value=p.roughnessMap,e(p.roughnessMap,m.roughnessMapTransform)),p.envMap&&(m.envMapIntensity.value=p.envMapIntensity)}function d(m,p,S){m.ior.value=p.ior,p.sheen>0&&(m.sheenColor.value.copy(p.sheenColor).multiplyScalar(p.sheen),m.sheenRoughness.value=p.sheenRoughness,p.sheenColorMap&&(m.sheenColorMap.value=p.sheenColorMap,e(p.sheenColorMap,m.sheenColorMapTransform)),p.sheenRoughnessMap&&(m.sheenRoughnessMap.value=p.sheenRoughnessMap,e(p.sheenRoughnessMap,m.sheenRoughnessMapTransform))),p.clearcoat>0&&(m.clearcoat.value=p.clearcoat,m.clearcoatRoughness.value=p.clearcoatRoughness,p.clearcoatMap&&(m.clearcoatMap.value=p.clearcoatMap,e(p.clearcoatMap,m.clearcoatMapTransform)),p.clearcoatRoughnessMap&&(m.clearcoatRoughnessMap.value=p.clearcoatRoughnessMap,e(p.clearcoatRoughnessMap,m.clearcoatRoughnessMapTransform)),p.clearcoatNormalMap&&(m.clearcoatNormalMap.value=p.clearcoatNormalMap,e(p.clearcoatNormalMap,m.clearcoatNormalMapTransform),m.clearcoatNormalScale.value.copy(p.clearcoatNormalScale),p.side===wn&&m.clearcoatNormalScale.value.negate())),p.dispersion>0&&(m.dispersion.value=p.dispersion),p.iridescence>0&&(m.iridescence.value=p.iridescence,m.iridescenceIOR.value=p.iridescenceIOR,m.iridescenceThicknessMinimum.value=p.iridescenceThicknessRange[0],m.iridescenceThicknessMaximum.value=p.iridescenceThicknessRange[1],p.iridescenceMap&&(m.iridescenceMap.value=p.iridescenceMap,e(p.iridescenceMap,m.iridescenceMapTransform)),p.iridescenceThicknessMap&&(m.iridescenceThicknessMap.value=p.iridescenceThicknessMap,e(p.iridescenceThicknessMap,m.iridescenceThicknessMapTransform))),p.transmission>0&&(m.transmission.value=p.transmission,m.transmissionSamplerMap.value=S.texture,m.transmissionSamplerSize.value.set(S.width,S.height),p.transmissionMap&&(m.transmissionMap.value=p.transmissionMap,e(p.transmissionMap,m.transmissionMapTransform)),m.thickness.value=p.thickness,p.thicknessMap&&(m.thicknessMap.value=p.thicknessMap,e(p.thicknessMap,m.thicknessMapTransform)),m.attenuationDistance.value=p.attenuationDistance,m.attenuationColor.value.copy(p.attenuationColor)),p.anisotropy>0&&(m.anisotropyVector.value.set(p.anisotropy*Math.cos(p.anisotropyRotation),p.anisotropy*Math.sin(p.anisotropyRotation)),p.anisotropyMap&&(m.anisotropyMap.value=p.anisotropyMap,e(p.anisotropyMap,m.anisotropyMapTransform))),m.specularIntensity.value=p.specularIntensity,m.specularColor.value.copy(p.specularColor),p.specularColorMap&&(m.specularColorMap.value=p.specularColorMap,e(p.specularColorMap,m.specularColorMapTransform)),p.specularIntensityMap&&(m.specularIntensityMap.value=p.specularIntensityMap,e(p.specularIntensityMap,m.specularIntensityMapTransform))}function g(m,p){p.matcap&&(m.matcap.value=p.matcap)}function _(m,p){let S=t.get(p).light;m.referencePosition.value.setFromMatrixPosition(S.matrixWorld),m.nearDistance.value=S.shadow.camera.near,m.farDistance.value=S.shadow.camera.far}return{refreshFogUniforms:n,refreshMaterialUniforms:i}}function lw(s,t,e,n){let i={},r={},o=[],a=s.getParameter(s.MAX_UNIFORM_BUFFER_BINDINGS);function l(S,y){let v=y.program;n.uniformBlockBinding(S,v)}function c(S,y){let v=i[S.id];v===void 0&&(g(S),v=h(S),i[S.id]=v,S.addEventListener("dispose",m));let E=y.program;n.updateUBOMapping(S,E);let A=t.render.frame;r[S.id]!==A&&(f(S),r[S.id]=A)}function h(S){let y=u();S.__bindingPointIndex=y;let v=s.createBuffer(),E=S.__size,A=S.usage;return s.bindBuffer(s.UNIFORM_BUFFER,v),s.bufferData(s.UNIFORM_BUFFER,E,A),s.bindBuffer(s.UNIFORM_BUFFER,null),s.bindBufferBase(s.UNIFORM_BUFFER,y,v),v}function u(){for(let S=0;S<a;S++)if(o.indexOf(S)===-1)return o.push(S),S;return console.error("THREE.WebGLRenderer: Maximum number of simultaneously usable uniforms groups reached."),0}function f(S){let y=i[S.id],v=S.uniforms,E=S.__cache;s.bindBuffer(s.UNIFORM_BUFFER,y);for(let A=0,T=v.length;A<T;A++){let R=Array.isArray(v[A])?v[A]:[v[A]];for(let M=0,x=R.length;M<x;M++){let L=R[M];if(d(L,A,M,E)===!0){let U=L.__offset,F=Array.isArray(L.value)?L.value:[L.value],z=0;for(let q=0;q<F.length;q++){let H=F[q],W=_(H);typeof H=="number"||typeof H=="boolean"?(L.__data[0]=H,s.bufferSubData(s.UNIFORM_BUFFER,U+z,L.__data)):H.isMatrix3?(L.__data[0]=H.elements[0],L.__data[1]=H.elements[1],L.__data[2]=H.elements[2],L.__data[3]=0,L.__data[4]=H.elements[3],L.__data[5]=H.elements[4],L.__data[6]=H.elements[5],L.__data[7]=0,L.__data[8]=H.elements[6],L.__data[9]=H.elements[7],L.__data[10]=H.elements[8],L.__data[11]=0):(H.toArray(L.__data,z),z+=W.storage/Float32Array.BYTES_PER_ELEMENT)}s.bufferSubData(s.UNIFORM_BUFFER,U,L.__data)}}}s.bindBuffer(s.UNIFORM_BUFFER,null)}function d(S,y,v,E){let A=S.value,T=y+"_"+v;if(E[T]===void 0)return typeof A=="number"||typeof A=="boolean"?E[T]=A:E[T]=A.clone(),!0;{let R=E[T];if(typeof A=="number"||typeof A=="boolean"){if(R!==A)return E[T]=A,!0}else if(R.equals(A)===!1)return R.copy(A),!0}return!1}function g(S){let y=S.uniforms,v=0,E=16;for(let T=0,R=y.length;T<R;T++){let M=Array.isArray(y[T])?y[T]:[y[T]];for(let x=0,L=M.length;x<L;x++){let U=M[x],F=Array.isArray(U.value)?U.value:[U.value];for(let z=0,q=F.length;z<q;z++){let H=F[z],W=_(H),V=v%E,st=V%W.boundary,I=V+st;v+=st,I!==0&&E-I<W.storage&&(v+=E-I),U.__data=new Float32Array(W.storage/Float32Array.BYTES_PER_ELEMENT),U.__offset=v,v+=W.storage}}}let A=v%E;return A>0&&(v+=E-A),S.__size=v,S.__cache={},this}function _(S){let y={boundary:0,storage:0};return typeof S=="number"||typeof S=="boolean"?(y.boundary=4,y.storage=4):S.isVector2?(y.boundary=8,y.storage=8):S.isVector3||S.isColor?(y.boundary=16,y.storage=12):S.isVector4?(y.boundary=16,y.storage=16):S.isMatrix3?(y.boundary=48,y.storage=48):S.isMatrix4?(y.boundary=64,y.storage=64):S.isTexture?console.warn("THREE.WebGLRenderer: Texture samplers can not be part of an uniforms group."):console.warn("THREE.WebGLRenderer: Unsupported uniform value type.",S),y}function m(S){let y=S.target;y.removeEventListener("dispose",m);let v=o.indexOf(y.__bindingPointIndex);o.splice(v,1),s.deleteBuffer(i[y.id]),delete i[y.id],delete r[y.id]}function p(){for(let S in i)s.deleteBuffer(i[S]);o=[],i={},r={}}return{bind:l,update:c,dispose:p}}var Dc=class{constructor(t={}){let{canvas:e=dy(),context:n=null,depth:i=!0,stencil:r=!1,alpha:o=!1,antialias:a=!1,premultipliedAlpha:l=!0,preserveDrawingBuffer:c=!1,powerPreference:h="default",failIfMajorPerformanceCaveat:u=!1,reverseDepthBuffer:f=!1}=t;this.isWebGLRenderer=!0;let d;if(n!==null){if(typeof WebGLRenderingContext<"u"&&n instanceof WebGLRenderingContext)throw new Error("THREE.WebGLRenderer: WebGL 1 is not supported since r163.");d=n.getContextAttributes().alpha}else d=o;let g=new Uint32Array(4),_=new Int32Array(4),m=null,p=null,S=[],y=[];this.domElement=e,this.debug={checkShaderErrors:!0,onShaderError:null},this.autoClear=!0,this.autoClearColor=!0,this.autoClearDepth=!0,this.autoClearStencil=!0,this.sortObjects=!0,this.clippingPlanes=[],this.localClippingEnabled=!1,this._outputColorSpace=Mn,this.toneMapping=Os,this.toneMappingExposure=1;let v=this,E=!1,A=0,T=0,R=null,M=-1,x=null,L=new Ae,U=new Ae,F=null,z=new se(0),q=0,H=e.width,W=e.height,V=1,st=null,I=null,at=new Ae(0,0,H,W),Dt=new Ae(0,0,H,W),Vt=!1,Z=new Va,rt=!1,St=!1,ot=new Ce,Rt=new Ce,Bt=new B,Wt=new Ae,Xt={background:null,fog:null,environment:null,overrideMaterial:null,isScene:!0},et=!1;function nt(){return R===null?V:1}let P=n;function It(w,N){return e.getContext(w,N)}try{let w={alpha:!0,depth:i,stencil:r,antialias:a,premultipliedAlpha:l,preserveDrawingBuffer:c,powerPreference:h,failIfMajorPerformanceCaveat:u};if("setAttribute"in e&&e.setAttribute("data-engine","three.js r170"),e.addEventListener("webglcontextlost",tt,!1),e.addEventListener("webglcontextrestored",Mt,!1),e.addEventListener("webglcontextcreationerror",wt,!1),P===null){let N="webgl2";if(P=It(N,w),P===null)throw It(N)?new Error("Error creating WebGL context with your selected attributes."):new Error("Error creating WebGL context.")}}catch(w){throw console.error("THREE.WebGLRenderer: "+w.message),w}let lt,O,dt,zt,At,C,b,X,Q,it,j,xt,pt,bt,Kt,ut,gt,qt,Yt,Lt,ee,Jt,Qt,D;function yt(){lt=new wb(P),lt.init(),Jt=new nw(P,lt),O=new vb(P,lt,t,Jt),dt=new j1(P,lt),O.reverseDepthBuffer&&f&&dt.buffers.depth.setReversed(!0),zt=new Ab(P),At=new z1,C=new ew(P,lt,dt,At,O,Jt,zt),b=new yb(v),X=new bb(v),Q=new Uy(P),Qt=new gb(P,Q),it=new Tb(P,Q,zt,Qt),j=new Rb(P,it,Q,zt),Yt=new Cb(P,O,C),ut=new xb(At),xt=new k1(v,b,X,lt,O,Qt,ut),pt=new aw(v,At),bt=new H1,Kt=new Z1(lt),qt=new mb(v,b,X,dt,j,d,l),gt=new K1(v,j,O),D=new lw(P,zt,O,dt),Lt=new _b(P,lt,zt),ee=new Eb(P,lt,zt),zt.programs=xt.programs,v.capabilities=O,v.extensions=lt,v.properties=At,v.renderLists=bt,v.shadowMap=gt,v.state=dt,v.info=zt}yt();let $=new hd(v,P);this.xr=$,this.getContext=function(){return P},this.getContextAttributes=function(){return P.getContextAttributes()},this.forceContextLoss=function(){let w=lt.get("WEBGL_lose_context");w&&w.loseContext()},this.forceContextRestore=function(){let w=lt.get("WEBGL_lose_context");w&&w.restoreContext()},this.getPixelRatio=function(){return V},this.setPixelRatio=function(w){w!==void 0&&(V=w,this.setSize(H,W,!1))},this.getSize=function(w){return w.set(H,W)},this.setSize=function(w,N,G=!0){if($.isPresenting){console.warn("THREE.WebGLRenderer: Can't change size while VR device is presenting.");return}H=w,W=N,e.width=Math.floor(w*V),e.height=Math.floor(N*V),G===!0&&(e.style.width=w+"px",e.style.height=N+"px"),this.setViewport(0,0,w,N)},this.getDrawingBufferSize=function(w){return w.set(H*V,W*V).floor()},this.setDrawingBufferSize=function(w,N,G){H=w,W=N,V=G,e.width=Math.floor(w*G),e.height=Math.floor(N*G),this.setViewport(0,0,w,N)},this.getCurrentViewport=function(w){return w.copy(L)},this.getViewport=function(w){return w.copy(at)},this.setViewport=function(w,N,G,Y){w.isVector4?at.set(w.x,w.y,w.z,w.w):at.set(w,N,G,Y),dt.viewport(L.copy(at).multiplyScalar(V).round())},this.getScissor=function(w){return w.copy(Dt)},this.setScissor=function(w,N,G,Y){w.isVector4?Dt.set(w.x,w.y,w.z,w.w):Dt.set(w,N,G,Y),dt.scissor(U.copy(Dt).multiplyScalar(V).round())},this.getScissorTest=function(){return Vt},this.setScissorTest=function(w){dt.setScissorTest(Vt=w)},this.setOpaqueSort=function(w){st=w},this.setTransparentSort=function(w){I=w},this.getClearColor=function(w){return w.copy(qt.getClearColor())},this.setClearColor=function(){qt.setClearColor.apply(qt,arguments)},this.getClearAlpha=function(){return qt.getClearAlpha()},this.setClearAlpha=function(){qt.setClearAlpha.apply(qt,arguments)},this.clear=function(w=!0,N=!0,G=!0){let Y=0;if(w){let k=!1;if(R!==null){let mt=R.texture.format;k=mt===Wd||mt===Gd||mt===Hd}if(k){let mt=R.texture.type,_t=mt===os||mt===Mr||mt===za||mt===Ao||mt===kd||mt===zd,Ct=qt.getClearColor(),Ot=qt.getClearAlpha(),te=Ct.r,ne=Ct.g,kt=Ct.b;_t?(g[0]=te,g[1]=ne,g[2]=kt,g[3]=Ot,P.clearBufferuiv(P.COLOR,0,g)):(_[0]=te,_[1]=ne,_[2]=kt,_[3]=Ot,P.clearBufferiv(P.COLOR,0,_))}else Y|=P.COLOR_BUFFER_BIT}N&&(Y|=P.DEPTH_BUFFER_BIT),G&&(Y|=P.STENCIL_BUFFER_BIT,this.state.buffers.stencil.setMask(4294967295)),P.clear(Y)},this.clearColor=function(){this.clear(!0,!1,!1)},this.clearDepth=function(){this.clear(!1,!0,!1)},this.clearStencil=function(){this.clear(!1,!1,!0)},this.dispose=function(){e.removeEventListener("webglcontextlost",tt,!1),e.removeEventListener("webglcontextrestored",Mt,!1),e.removeEventListener("webglcontextcreationerror",wt,!1),bt.dispose(),Kt.dispose(),At.dispose(),b.dispose(),X.dispose(),j.dispose(),Qt.dispose(),D.dispose(),xt.dispose(),$.dispose(),$.removeEventListener("sessionstart",ct),$.removeEventListener("sessionend",Nt),Et.stop()};function tt(w){w.preventDefault(),console.log("THREE.WebGLRenderer: Context Lost."),E=!0}function Mt(){console.log("THREE.WebGLRenderer: Context Restored."),E=!1;let w=zt.autoReset,N=gt.enabled,G=gt.autoUpdate,Y=gt.needsUpdate,k=gt.type;yt(),zt.autoReset=w,gt.enabled=N,gt.autoUpdate=G,gt.needsUpdate=Y,gt.type=k}function wt(w){console.error("THREE.WebGLRenderer: A WebGL context could not be created. Reason: ",w.statusMessage)}function K(w){let N=w.target;N.removeEventListener("dispose",K),ft(N)}function ft(w){Ut(w),At.remove(w)}function Ut(w){let N=At.get(w).programs;N!==void 0&&(N.forEach(function(G){xt.releaseProgram(G)}),w.isShaderMaterial&&xt.releaseShaderCache(w))}this.renderBufferDirect=function(w,N,G,Y,k,mt){N===null&&(N=Xt);let _t=k.isMesh&&k.matrixWorld.determinant()<0,Ct=Ye(w,N,G,Y,k);dt.setMaterial(Y,_t);let Ot=G.index,te=1;if(Y.wireframe===!0){if(Ot=it.getWireframeAttribute(G),Ot===void 0)return;te=2}let ne=G.drawRange,kt=G.attributes.position,re=ne.start*te,xe=(ne.start+ne.count)*te;mt!==null&&(re=Math.max(re,mt.start*te),xe=Math.min(xe,(mt.start+mt.count)*te)),Ot!==null?(re=Math.max(re,0),xe=Math.min(xe,Ot.count)):kt!=null&&(re=Math.max(re,0),xe=Math.min(xe,kt.count));let ye=xe-re;if(ye<0||ye===1/0)return;Qt.setup(k,Y,Ct,G,Ot);let Fe,Me=Lt;if(Ot!==null&&(Fe=Q.get(Ot),Me=ee,Me.setIndex(Fe)),k.isMesh)Y.wireframe===!0?(dt.setLineWidth(Y.wireframeLinewidth*nt()),Me.setMode(P.LINES)):Me.setMode(P.TRIANGLES);else if(k.isLine){let Zt=Y.linewidth;Zt===void 0&&(Zt=1),dt.setLineWidth(Zt*nt()),k.isLineSegments?Me.setMode(P.LINES):k.isLineLoop?Me.setMode(P.LINE_LOOP):Me.setMode(P.LINE_STRIP)}else k.isPoints?Me.setMode(P.POINTS):k.isSprite&&Me.setMode(P.TRIANGLES);if(k.isBatchedMesh)if(k._multiDrawInstances!==null)Me.renderMultiDrawInstances(k._multiDrawStarts,k._multiDrawCounts,k._multiDrawCount,k._multiDrawInstances);else if(lt.get("WEBGL_multi_draw"))Me.renderMultiDraw(k._multiDrawStarts,k._multiDrawCounts,k._multiDrawCount);else{let Zt=k._multiDrawStarts,zi=k._multiDrawCounts,Se=k._multiDrawCount,_i=Ot?Q.get(Ot).bytesPerElement:1,Dr=At.get(Y).currentProgram.getUniforms();for(let Gn=0;Gn<Se;Gn++)Dr.setValue(P,"_gl_DrawID",Gn),Me.render(Zt[Gn]/_i,zi[Gn])}else if(k.isInstancedMesh)Me.renderInstances(re,ye,k.count);else if(G.isInstancedBufferGeometry){let Zt=G._maxInstanceCount!==void 0?G._maxInstanceCount:1/0,zi=Math.min(G.instanceCount,Zt);Me.renderInstances(re,ye,zi)}else Me.render(re,ye)};function J(w,N,G){w.transparent===!0&&w.side===pi&&w.forceSinglePass===!1?(w.side=wn,w.needsUpdate=!0,de(w,N,G),w.side=Bs,w.needsUpdate=!0,de(w,N,G),w.side=pi):de(w,N,G)}this.compile=function(w,N,G=null){G===null&&(G=w),p=Kt.get(G),p.init(N),y.push(p),G.traverseVisible(function(k){k.isLight&&k.layers.test(N.layers)&&(p.pushLight(k),k.castShadow&&p.pushShadow(k))}),w!==G&&w.traverseVisible(function(k){k.isLight&&k.layers.test(N.layers)&&(p.pushLight(k),k.castShadow&&p.pushShadow(k))}),p.setupLights();let Y=new Set;return w.traverse(function(k){if(!(k.isMesh||k.isPoints||k.isLine||k.isSprite))return;let mt=k.material;if(mt)if(Array.isArray(mt))for(let _t=0;_t<mt.length;_t++){let Ct=mt[_t];J(Ct,G,k),Y.add(Ct)}else J(mt,G,k),Y.add(mt)}),y.pop(),p=null,Y},this.compileAsync=function(w,N,G=null){let Y=this.compile(w,N,G);return new Promise(k=>{function mt(){if(Y.forEach(function(_t){At.get(_t).currentProgram.isReady()&&Y.delete(_t)}),Y.size===0){k(w);return}setTimeout(mt,10)}lt.get("KHR_parallel_shader_compile")!==null?mt():setTimeout(mt,10)})};let ht=null;function Tt(w){ht&&ht(w)}function ct(){Et.stop()}function Nt(){Et.start()}let Et=new X_;Et.setAnimationLoop(Tt),typeof self<"u"&&Et.setContext(self),this.setAnimationLoop=function(w){ht=w,$.setAnimationLoop(w),w===null?Et.stop():Et.start()},$.addEventListener("sessionstart",ct),$.addEventListener("sessionend",Nt),this.render=function(w,N){if(N!==void 0&&N.isCamera!==!0){console.error("THREE.WebGLRenderer.render: camera is not an instance of THREE.Camera.");return}if(E===!0)return;if(w.matrixWorldAutoUpdate===!0&&w.updateMatrixWorld(),N.parent===null&&N.matrixWorldAutoUpdate===!0&&N.updateMatrixWorld(),$.enabled===!0&&$.isPresenting===!0&&($.cameraAutoUpdate===!0&&$.updateCamera(N),N=$.getCamera()),w.isScene===!0&&w.onBeforeRender(v,w,N,R),p=Kt.get(w,y.length),p.init(N),y.push(p),Rt.multiplyMatrices(N.projectionMatrix,N.matrixWorldInverse),Z.setFromProjectionMatrix(Rt),St=this.localClippingEnabled,rt=ut.init(this.clippingPlanes,St),m=bt.get(w,S.length),m.init(),S.push(m),$.enabled===!0&&$.isPresenting===!0){let mt=v.xr.getDepthSensingMesh();mt!==null&&Ht(mt,N,-1/0,v.sortObjects)}Ht(w,N,0,v.sortObjects),m.finish(),v.sortObjects===!0&&m.sort(st,I),et=$.enabled===!1||$.isPresenting===!1||$.hasDepthSensing()===!1,et&&qt.addToRenderList(m,w),this.info.render.frame++,rt===!0&&ut.beginShadows();let G=p.state.shadowsArray;gt.render(G,w,N),rt===!0&&ut.endShadows(),this.info.autoReset===!0&&this.info.reset();let Y=m.opaque,k=m.transmissive;if(p.setupLights(),N.isArrayCamera){let mt=N.cameras;if(k.length>0)for(let _t=0,Ct=mt.length;_t<Ct;_t++){let Ot=mt[_t];jt(Y,k,w,Ot)}et&&qt.render(w);for(let _t=0,Ct=mt.length;_t<Ct;_t++){let Ot=mt[_t];fe(m,w,Ot,Ot.viewport)}}else k.length>0&&jt(Y,k,w,N),et&&qt.render(w),fe(m,w,N);R!==null&&(C.updateMultisampleRenderTarget(R),C.updateRenderTargetMipmap(R)),w.isScene===!0&&w.onAfterRender(v,w,N),Qt.resetDefaultState(),M=-1,x=null,y.pop(),y.length>0?(p=y[y.length-1],rt===!0&&ut.setGlobalState(v.clippingPlanes,p.state.camera)):p=null,S.pop(),S.length>0?m=S[S.length-1]:m=null};function Ht(w,N,G,Y){if(w.visible===!1)return;if(w.layers.test(N.layers)){if(w.isGroup)G=w.renderOrder;else if(w.isLOD)w.autoUpdate===!0&&w.update(N);else if(w.isLight)p.pushLight(w),w.castShadow&&p.pushShadow(w);else if(w.isSprite){if(!w.frustumCulled||Z.intersectsSprite(w)){Y&&Wt.setFromMatrixPosition(w.matrixWorld).applyMatrix4(Rt);let _t=j.update(w),Ct=w.material;Ct.visible&&m.push(w,_t,Ct,G,Wt.z,null)}}else if((w.isMesh||w.isLine||w.isPoints)&&(!w.frustumCulled||Z.intersectsObject(w))){let _t=j.update(w),Ct=w.material;if(Y&&(w.boundingSphere!==void 0?(w.boundingSphere===null&&w.computeBoundingSphere(),Wt.copy(w.boundingSphere.center)):(_t.boundingSphere===null&&_t.computeBoundingSphere(),Wt.copy(_t.boundingSphere.center)),Wt.applyMatrix4(w.matrixWorld).applyMatrix4(Rt)),Array.isArray(Ct)){let Ot=_t.groups;for(let te=0,ne=Ot.length;te<ne;te++){let kt=Ot[te],re=Ct[kt.materialIndex];re&&re.visible&&m.push(w,_t,re,G,Wt.z,kt)}}else Ct.visible&&m.push(w,_t,Ct,G,Wt.z,null)}}let mt=w.children;for(let _t=0,Ct=mt.length;_t<Ct;_t++)Ht(mt[_t],N,G,Y)}function fe(w,N,G,Y){let k=w.opaque,mt=w.transmissive,_t=w.transparent;p.setupLightsView(G),rt===!0&&ut.setGlobalState(v.clippingPlanes,G),Y&&dt.viewport(L.copy(Y)),k.length>0&&_e(k,N,G),mt.length>0&&_e(mt,N,G),_t.length>0&&_e(_t,N,G),dt.buffers.depth.setTest(!0),dt.buffers.depth.setMask(!0),dt.buffers.color.setMask(!0),dt.setPolygonOffset(!1)}function jt(w,N,G,Y){if((G.isScene===!0?G.overrideMaterial:null)!==null)return;p.state.transmissionRenderTarget[Y.id]===void 0&&(p.state.transmissionRenderTarget[Y.id]=new un(1,1,{generateMipmaps:!0,type:lt.has("EXT_color_buffer_half_float")||lt.has("EXT_color_buffer_float")?ei:os,minFilter:yr,samples:4,stencilBuffer:r,resolveDepthBuffer:!1,resolveStencilBuffer:!1,colorSpace:ge.workingColorSpace}));let mt=p.state.transmissionRenderTarget[Y.id],_t=Y.viewport||L;mt.setSize(_t.z,_t.w);let Ct=v.getRenderTarget();v.setRenderTarget(mt),v.getClearColor(z),q=v.getClearAlpha(),q<1&&v.setClearColor(16777215,.5),v.clear(),et&&qt.render(G);let Ot=v.toneMapping;v.toneMapping=Os;let te=Y.viewport;if(Y.viewport!==void 0&&(Y.viewport=void 0),p.setupLightsView(Y),rt===!0&&ut.setGlobalState(v.clippingPlanes,Y),_e(w,G,Y),C.updateMultisampleRenderTarget(mt),C.updateRenderTargetMipmap(mt),lt.has("WEBGL_multisampled_render_to_texture")===!1){let ne=!1;for(let kt=0,re=N.length;kt<re;kt++){let xe=N[kt],ye=xe.object,Fe=xe.geometry,Me=xe.material,Zt=xe.group;if(Me.side===pi&&ye.layers.test(Y.layers)){let zi=Me.side;Me.side=wn,Me.needsUpdate=!0,Ue(ye,G,Y,Fe,Me,Zt),Me.side=zi,Me.needsUpdate=!0,ne=!0}}ne===!0&&(C.updateMultisampleRenderTarget(mt),C.updateRenderTargetMipmap(mt))}v.setRenderTarget(Ct),v.setClearColor(z,q),te!==void 0&&(Y.viewport=te),v.toneMapping=Ot}function _e(w,N,G){let Y=N.isScene===!0?N.overrideMaterial:null;for(let k=0,mt=w.length;k<mt;k++){let _t=w[k],Ct=_t.object,Ot=_t.geometry,te=Y===null?_t.material:Y,ne=_t.group;Ct.layers.test(G.layers)&&Ue(Ct,N,G,Ot,te,ne)}}function Ue(w,N,G,Y,k,mt){w.onBeforeRender(v,N,G,Y,k,mt),w.modelViewMatrix.multiplyMatrices(G.matrixWorldInverse,w.matrixWorld),w.normalMatrix.getNormalMatrix(w.modelViewMatrix),k.onBeforeRender(v,N,G,Y,w,mt),k.transparent===!0&&k.side===pi&&k.forceSinglePass===!1?(k.side=wn,k.needsUpdate=!0,v.renderBufferDirect(G,N,Y,k,w,mt),k.side=Bs,k.needsUpdate=!0,v.renderBufferDirect(G,N,Y,k,w,mt),k.side=pi):v.renderBufferDirect(G,N,Y,k,w,mt),w.onAfterRender(v,N,G,Y,k,mt)}function de(w,N,G){N.isScene!==!0&&(N=Xt);let Y=At.get(w),k=p.state.lights,mt=p.state.shadowsArray,_t=k.state.version,Ct=xt.getParameters(w,k.state,mt,N,G),Ot=xt.getProgramCacheKey(Ct),te=Y.programs;Y.environment=w.isMeshStandardMaterial?N.environment:null,Y.fog=N.fog,Y.envMap=(w.isMeshStandardMaterial?X:b).get(w.envMap||Y.environment),Y.envMapRotation=Y.environment!==null&&w.envMap===null?N.environmentRotation:w.envMapRotation,te===void 0&&(w.addEventListener("dispose",K),te=new Map,Y.programs=te);let ne=te.get(Ot);if(ne!==void 0){if(Y.currentProgram===ne&&Y.lightsStateVersion===_t)return ae(w,Ct),ne}else Ct.uniforms=xt.getUniforms(w),w.onBeforeCompile(Ct,v),ne=xt.acquireProgram(Ct,Ot),te.set(Ot,ne),Y.uniforms=Ct.uniforms;let kt=Y.uniforms;return(!w.isShaderMaterial&&!w.isRawShaderMaterial||w.clipping===!0)&&(kt.clippingPlanes=ut.uniform),ae(w,Ct),Y.needsLights=qe(w),Y.lightsStateVersion=_t,Y.needsLights&&(kt.ambientLightColor.value=k.state.ambient,kt.lightProbe.value=k.state.probe,kt.directionalLights.value=k.state.directional,kt.directionalLightShadows.value=k.state.directionalShadow,kt.spotLights.value=k.state.spot,kt.spotLightShadows.value=k.state.spotShadow,kt.rectAreaLights.value=k.state.rectArea,kt.ltc_1.value=k.state.rectAreaLTC1,kt.ltc_2.value=k.state.rectAreaLTC2,kt.pointLights.value=k.state.point,kt.pointLightShadows.value=k.state.pointShadow,kt.hemisphereLights.value=k.state.hemi,kt.directionalShadowMap.value=k.state.directionalShadowMap,kt.directionalShadowMatrix.value=k.state.directionalShadowMatrix,kt.spotShadowMap.value=k.state.spotShadowMap,kt.spotLightMatrix.value=k.state.spotLightMatrix,kt.spotLightMap.value=k.state.spotLightMap,kt.pointShadowMap.value=k.state.pointShadowMap,kt.pointShadowMatrix.value=k.state.pointShadowMatrix),Y.currentProgram=ne,Y.uniformsList=null,ne}function pe(w){if(w.uniformsList===null){let N=w.currentProgram.getUniforms();w.uniformsList=bo.seqWithValue(N.seq,w.uniforms)}return w.uniformsList}function ae(w,N){let G=At.get(w);G.outputColorSpace=N.outputColorSpace,G.batching=N.batching,G.batchingColor=N.batchingColor,G.instancing=N.instancing,G.instancingColor=N.instancingColor,G.instancingMorph=N.instancingMorph,G.skinning=N.skinning,G.morphTargets=N.morphTargets,G.morphNormals=N.morphNormals,G.morphColors=N.morphColors,G.morphTargetsCount=N.morphTargetsCount,G.numClippingPlanes=N.numClippingPlanes,G.numIntersection=N.numClipIntersection,G.vertexAlphas=N.vertexAlphas,G.vertexTangents=N.vertexTangents,G.toneMapping=N.toneMapping}function Ye(w,N,G,Y,k){N.isScene!==!0&&(N=Xt),C.resetTextureUnits();let mt=N.fog,_t=Y.isMeshStandardMaterial?N.environment:null,Ct=R===null?v.outputColorSpace:R.isXRRenderTarget===!0?R.texture.colorSpace:Oo,Ot=(Y.isMeshStandardMaterial?X:b).get(Y.envMap||_t),te=Y.vertexColors===!0&&!!G.attributes.color&&G.attributes.color.itemSize===4,ne=!!G.attributes.tangent&&(!!Y.normalMap||Y.anisotropy>0),kt=!!G.morphAttributes.position,re=!!G.morphAttributes.normal,xe=!!G.morphAttributes.color,ye=Os;Y.toneMapped&&(R===null||R.isXRRenderTarget===!0)&&(ye=v.toneMapping);let Fe=G.morphAttributes.position||G.morphAttributes.normal||G.morphAttributes.color,Me=Fe!==void 0?Fe.length:0,Zt=At.get(Y),zi=p.state.lights;if(rt===!0&&(St===!0||w!==x)){let oi=w===x&&Y.id===M;ut.setState(Y,w,oi)}let Se=!1;Y.version===Zt.__version?(Zt.needsLights&&Zt.lightsStateVersion!==zi.state.version||Zt.outputColorSpace!==Ct||k.isBatchedMesh&&Zt.batching===!1||!k.isBatchedMesh&&Zt.batching===!0||k.isBatchedMesh&&Zt.batchingColor===!0&&k.colorTexture===null||k.isBatchedMesh&&Zt.batchingColor===!1&&k.colorTexture!==null||k.isInstancedMesh&&Zt.instancing===!1||!k.isInstancedMesh&&Zt.instancing===!0||k.isSkinnedMesh&&Zt.skinning===!1||!k.isSkinnedMesh&&Zt.skinning===!0||k.isInstancedMesh&&Zt.instancingColor===!0&&k.instanceColor===null||k.isInstancedMesh&&Zt.instancingColor===!1&&k.instanceColor!==null||k.isInstancedMesh&&Zt.instancingMorph===!0&&k.morphTexture===null||k.isInstancedMesh&&Zt.instancingMorph===!1&&k.morphTexture!==null||Zt.envMap!==Ot||Y.fog===!0&&Zt.fog!==mt||Zt.numClippingPlanes!==void 0&&(Zt.numClippingPlanes!==ut.numPlanes||Zt.numIntersection!==ut.numIntersection)||Zt.vertexAlphas!==te||Zt.vertexTangents!==ne||Zt.morphTargets!==kt||Zt.morphNormals!==re||Zt.morphColors!==xe||Zt.toneMapping!==ye||Zt.morphTargetsCount!==Me)&&(Se=!0):(Se=!0,Zt.__version=Y.version);let _i=Zt.currentProgram;Se===!0&&(_i=de(Y,N,k));let Dr=!1,Gn=!1,Wo=!1,De=_i.getUniforms(),Ri=Zt.uniforms;if(dt.useProgram(_i.program)&&(Dr=!0,Gn=!0,Wo=!0),Y.id!==M&&(M=Y.id,Gn=!0),Dr||x!==w){dt.buffers.depth.getReversed()?(ot.copy(w.projectionMatrix),my(ot),gy(ot),De.setValue(P,"projectionMatrix",ot)):De.setValue(P,"projectionMatrix",w.projectionMatrix),De.setValue(P,"viewMatrix",w.matrixWorldInverse);let fs=De.map.cameraPosition;fs!==void 0&&fs.setValue(P,Bt.setFromMatrixPosition(w.matrixWorld)),O.logarithmicDepthBuffer&&De.setValue(P,"logDepthBufFC",2/(Math.log(w.far+1)/Math.LN2)),(Y.isMeshPhongMaterial||Y.isMeshToonMaterial||Y.isMeshLambertMaterial||Y.isMeshBasicMaterial||Y.isMeshStandardMaterial||Y.isShaderMaterial)&&De.setValue(P,"isOrthographic",w.isOrthographicCamera===!0),x!==w&&(x=w,Gn=!0,Wo=!0)}if(k.isSkinnedMesh){De.setOptional(P,k,"bindMatrix"),De.setOptional(P,k,"bindMatrixInverse");let oi=k.skeleton;oi&&(oi.boneTexture===null&&oi.computeBoneTexture(),De.setValue(P,"boneTexture",oi.boneTexture,C))}k.isBatchedMesh&&(De.setOptional(P,k,"batchingTexture"),De.setValue(P,"batchingTexture",k._matricesTexture,C),De.setOptional(P,k,"batchingIdTexture"),De.setValue(P,"batchingIdTexture",k._indirectTexture,C),De.setOptional(P,k,"batchingColorTexture"),k._colorsTexture!==null&&De.setValue(P,"batchingColorTexture",k._colorsTexture,C));let Xo=G.morphAttributes;if((Xo.position!==void 0||Xo.normal!==void 0||Xo.color!==void 0)&&Yt.update(k,G,_i),(Gn||Zt.receiveShadow!==k.receiveShadow)&&(Zt.receiveShadow=k.receiveShadow,De.setValue(P,"receiveShadow",k.receiveShadow)),Y.isMeshGouraudMaterial&&Y.envMap!==null&&(Ri.envMap.value=Ot,Ri.flipEnvMap.value=Ot.isCubeTexture&&Ot.isRenderTargetTexture===!1?-1:1),Y.isMeshStandardMaterial&&Y.envMap===null&&N.environment!==null&&(Ri.envMapIntensity.value=N.environmentIntensity),Gn&&(De.setValue(P,"toneMappingExposure",v.toneMappingExposure),Zt.needsLights&&Re(Ri,Wo),mt&&Y.fog===!0&&pt.refreshFogUniforms(Ri,mt),pt.refreshMaterialUniforms(Ri,Y,V,W,p.state.transmissionRenderTarget[w.id]),bo.upload(P,pe(Zt),Ri,C)),Y.isShaderMaterial&&Y.uniformsNeedUpdate===!0&&(bo.upload(P,pe(Zt),Ri,C),Y.uniformsNeedUpdate=!1),Y.isSpriteMaterial&&De.setValue(P,"center",k.center),De.setValue(P,"modelViewMatrix",k.modelViewMatrix),De.setValue(P,"normalMatrix",k.normalMatrix),De.setValue(P,"modelMatrix",k.matrixWorld),Y.isShaderMaterial||Y.isRawShaderMaterial){let oi=Y.uniformsGroups;for(let fs=0,ds=oi.length;fs<ds;fs++){let lp=oi[fs];D.update(lp,_i),D.bind(lp,_i)}}return _i}function Re(w,N){w.ambientLightColor.needsUpdate=N,w.lightProbe.needsUpdate=N,w.directionalLights.needsUpdate=N,w.directionalLightShadows.needsUpdate=N,w.pointLights.needsUpdate=N,w.pointLightShadows.needsUpdate=N,w.spotLights.needsUpdate=N,w.spotLightShadows.needsUpdate=N,w.rectAreaLights.needsUpdate=N,w.hemisphereLights.needsUpdate=N}function qe(w){return w.isMeshLambertMaterial||w.isMeshToonMaterial||w.isMeshPhongMaterial||w.isMeshStandardMaterial||w.isShadowMaterial||w.isShaderMaterial&&w.lights===!0}this.getActiveCubeFace=function(){return A},this.getActiveMipmapLevel=function(){return T},this.getRenderTarget=function(){return R},this.setRenderTargetTextures=function(w,N,G){At.get(w.texture).__webglTexture=N,At.get(w.depthTexture).__webglTexture=G;let Y=At.get(w);Y.__hasExternalTextures=!0,Y.__autoAllocateDepthBuffer=G===void 0,Y.__autoAllocateDepthBuffer||lt.has("WEBGL_multisampled_render_to_texture")===!0&&(console.warn("THREE.WebGLRenderer: Render-to-texture extension was disabled because an external texture was provided"),Y.__useRenderToTexture=!1)},this.setRenderTargetFramebuffer=function(w,N){let G=At.get(w);G.__webglFramebuffer=N,G.__useDefaultFramebuffer=N===void 0},this.setRenderTarget=function(w,N=0,G=0){R=w,A=N,T=G;let Y=!0,k=null,mt=!1,_t=!1;if(w){let Ot=At.get(w);if(Ot.__useDefaultFramebuffer!==void 0)dt.bindFramebuffer(P.FRAMEBUFFER,null),Y=!1;else if(Ot.__webglFramebuffer===void 0)C.setupRenderTarget(w);else if(Ot.__hasExternalTextures)C.rebindTextures(w,At.get(w.texture).__webglTexture,At.get(w.depthTexture).__webglTexture);else if(w.depthBuffer){let kt=w.depthTexture;if(Ot.__boundDepthTexture!==kt){if(kt!==null&&At.has(kt)&&(w.width!==kt.image.width||w.height!==kt.image.height))throw new Error("WebGLRenderTarget: Attached DepthTexture is initialized to the incorrect size.");C.setupDepthRenderbuffer(w)}}let te=w.texture;(te.isData3DTexture||te.isDataArrayTexture||te.isCompressedArrayTexture)&&(_t=!0);let ne=At.get(w).__webglFramebuffer;w.isWebGLCubeRenderTarget?(Array.isArray(ne[N])?k=ne[N][G]:k=ne[N],mt=!0):w.samples>0&&C.useMultisampledRTT(w)===!1?k=At.get(w).__webglMultisampledFramebuffer:Array.isArray(ne)?k=ne[G]:k=ne,L.copy(w.viewport),U.copy(w.scissor),F=w.scissorTest}else L.copy(at).multiplyScalar(V).floor(),U.copy(Dt).multiplyScalar(V).floor(),F=Vt;if(dt.bindFramebuffer(P.FRAMEBUFFER,k)&&Y&&dt.drawBuffers(w,k),dt.viewport(L),dt.scissor(U),dt.setScissorTest(F),mt){let Ot=At.get(w.texture);P.framebufferTexture2D(P.FRAMEBUFFER,P.COLOR_ATTACHMENT0,P.TEXTURE_CUBE_MAP_POSITIVE_X+N,Ot.__webglTexture,G)}else if(_t){let Ot=At.get(w.texture),te=N||0;P.framebufferTextureLayer(P.FRAMEBUFFER,P.COLOR_ATTACHMENT0,Ot.__webglTexture,G||0,te)}M=-1},this.readRenderTargetPixels=function(w,N,G,Y,k,mt,_t){if(!(w&&w.isWebGLRenderTarget)){console.error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not THREE.WebGLRenderTarget.");return}let Ct=At.get(w).__webglFramebuffer;if(w.isWebGLCubeRenderTarget&&_t!==void 0&&(Ct=Ct[_t]),Ct){dt.bindFramebuffer(P.FRAMEBUFFER,Ct);try{let Ot=w.texture,te=Ot.format,ne=Ot.type;if(!O.textureFormatReadable(te)){console.error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not in RGBA or implementation defined format.");return}if(!O.textureTypeReadable(ne)){console.error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not in UnsignedByteType or implementation defined type.");return}N>=0&&N<=w.width-Y&&G>=0&&G<=w.height-k&&P.readPixels(N,G,Y,k,Jt.convert(te),Jt.convert(ne),mt)}finally{let Ot=R!==null?At.get(R).__webglFramebuffer:null;dt.bindFramebuffer(P.FRAMEBUFFER,Ot)}}},this.readRenderTargetPixelsAsync=async function(w,N,G,Y,k,mt,_t){if(!(w&&w.isWebGLRenderTarget))throw new Error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not THREE.WebGLRenderTarget.");let Ct=At.get(w).__webglFramebuffer;if(w.isWebGLCubeRenderTarget&&_t!==void 0&&(Ct=Ct[_t]),Ct){let Ot=w.texture,te=Ot.format,ne=Ot.type;if(!O.textureFormatReadable(te))throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: renderTarget is not in RGBA or implementation defined format.");if(!O.textureTypeReadable(ne))throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: renderTarget is not in UnsignedByteType or implementation defined type.");if(N>=0&&N<=w.width-Y&&G>=0&&G<=w.height-k){dt.bindFramebuffer(P.FRAMEBUFFER,Ct);let kt=P.createBuffer();P.bindBuffer(P.PIXEL_PACK_BUFFER,kt),P.bufferData(P.PIXEL_PACK_BUFFER,mt.byteLength,P.STREAM_READ),P.readPixels(N,G,Y,k,Jt.convert(te),Jt.convert(ne),0);let re=R!==null?At.get(R).__webglFramebuffer:null;dt.bindFramebuffer(P.FRAMEBUFFER,re);let xe=P.fenceSync(P.SYNC_GPU_COMMANDS_COMPLETE,0);return P.flush(),await py(P,xe,4),P.bindBuffer(P.PIXEL_PACK_BUFFER,kt),P.getBufferSubData(P.PIXEL_PACK_BUFFER,0,mt),P.deleteBuffer(kt),P.deleteSync(xe),mt}else throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: requested read bounds are out of range.")}},this.copyFramebufferToTexture=function(w,N=null,G=0){w.isTexture!==!0&&(Na("WebGLRenderer: copyFramebufferToTexture function signature has changed."),N=arguments[0]||null,w=arguments[1]);let Y=Math.pow(2,-G),k=Math.floor(w.image.width*Y),mt=Math.floor(w.image.height*Y),_t=N!==null?N.x:0,Ct=N!==null?N.y:0;C.setTexture2D(w,0),P.copyTexSubImage2D(P.TEXTURE_2D,G,0,0,_t,Ct,k,mt),dt.unbindTexture()},this.copyTextureToTexture=function(w,N,G=null,Y=null,k=0){w.isTexture!==!0&&(Na("WebGLRenderer: copyTextureToTexture function signature has changed."),Y=arguments[0]||null,w=arguments[1],N=arguments[2],k=arguments[3]||0,G=null);let mt,_t,Ct,Ot,te,ne,kt,re,xe,ye=w.isCompressedTexture?w.mipmaps[k]:w.image;G!==null?(mt=G.max.x-G.min.x,_t=G.max.y-G.min.y,Ct=G.isBox3?G.max.z-G.min.z:1,Ot=G.min.x,te=G.min.y,ne=G.isBox3?G.min.z:0):(mt=ye.width,_t=ye.height,Ct=ye.depth||1,Ot=0,te=0,ne=0),Y!==null?(kt=Y.x,re=Y.y,xe=Y.z):(kt=0,re=0,xe=0);let Fe=Jt.convert(N.format),Me=Jt.convert(N.type),Zt;N.isData3DTexture?(C.setTexture3D(N,0),Zt=P.TEXTURE_3D):N.isDataArrayTexture||N.isCompressedArrayTexture?(C.setTexture2DArray(N,0),Zt=P.TEXTURE_2D_ARRAY):(C.setTexture2D(N,0),Zt=P.TEXTURE_2D),P.pixelStorei(P.UNPACK_FLIP_Y_WEBGL,N.flipY),P.pixelStorei(P.UNPACK_PREMULTIPLY_ALPHA_WEBGL,N.premultiplyAlpha),P.pixelStorei(P.UNPACK_ALIGNMENT,N.unpackAlignment);let zi=P.getParameter(P.UNPACK_ROW_LENGTH),Se=P.getParameter(P.UNPACK_IMAGE_HEIGHT),_i=P.getParameter(P.UNPACK_SKIP_PIXELS),Dr=P.getParameter(P.UNPACK_SKIP_ROWS),Gn=P.getParameter(P.UNPACK_SKIP_IMAGES);P.pixelStorei(P.UNPACK_ROW_LENGTH,ye.width),P.pixelStorei(P.UNPACK_IMAGE_HEIGHT,ye.height),P.pixelStorei(P.UNPACK_SKIP_PIXELS,Ot),P.pixelStorei(P.UNPACK_SKIP_ROWS,te),P.pixelStorei(P.UNPACK_SKIP_IMAGES,ne);let Wo=w.isDataArrayTexture||w.isData3DTexture,De=N.isDataArrayTexture||N.isData3DTexture;if(w.isRenderTargetTexture||w.isDepthTexture){let Ri=At.get(w),Xo=At.get(N),oi=At.get(Ri.__renderTarget),fs=At.get(Xo.__renderTarget);dt.bindFramebuffer(P.READ_FRAMEBUFFER,oi.__webglFramebuffer),dt.bindFramebuffer(P.DRAW_FRAMEBUFFER,fs.__webglFramebuffer);for(let ds=0;ds<Ct;ds++)Wo&&P.framebufferTextureLayer(P.READ_FRAMEBUFFER,P.COLOR_ATTACHMENT0,At.get(w).__webglTexture,k,ne+ds),w.isDepthTexture?(De&&P.framebufferTextureLayer(P.DRAW_FRAMEBUFFER,P.COLOR_ATTACHMENT0,At.get(N).__webglTexture,k,xe+ds),P.blitFramebuffer(Ot,te,mt,_t,kt,re,mt,_t,P.DEPTH_BUFFER_BIT,P.NEAREST)):De?P.copyTexSubImage3D(Zt,k,kt,re,xe+ds,Ot,te,mt,_t):P.copyTexSubImage2D(Zt,k,kt,re,xe+ds,Ot,te,mt,_t);dt.bindFramebuffer(P.READ_FRAMEBUFFER,null),dt.bindFramebuffer(P.DRAW_FRAMEBUFFER,null)}else De?w.isDataTexture||w.isData3DTexture?P.texSubImage3D(Zt,k,kt,re,xe,mt,_t,Ct,Fe,Me,ye.data):N.isCompressedArrayTexture?P.compressedTexSubImage3D(Zt,k,kt,re,xe,mt,_t,Ct,Fe,ye.data):P.texSubImage3D(Zt,k,kt,re,xe,mt,_t,Ct,Fe,Me,ye):w.isDataTexture?P.texSubImage2D(P.TEXTURE_2D,k,kt,re,mt,_t,Fe,Me,ye.data):w.isCompressedTexture?P.compressedTexSubImage2D(P.TEXTURE_2D,k,kt,re,ye.width,ye.height,Fe,ye.data):P.texSubImage2D(P.TEXTURE_2D,k,kt,re,mt,_t,Fe,Me,ye);P.pixelStorei(P.UNPACK_ROW_LENGTH,zi),P.pixelStorei(P.UNPACK_IMAGE_HEIGHT,Se),P.pixelStorei(P.UNPACK_SKIP_PIXELS,_i),P.pixelStorei(P.UNPACK_SKIP_ROWS,Dr),P.pixelStorei(P.UNPACK_SKIP_IMAGES,Gn),k===0&&N.generateMipmaps&&P.generateMipmap(Zt),dt.unbindTexture()},this.copyTextureToTexture3D=function(w,N,G=null,Y=null,k=0){return w.isTexture!==!0&&(Na("WebGLRenderer: copyTextureToTexture3D function signature has changed."),G=arguments[0]||null,Y=arguments[1]||null,w=arguments[2],N=arguments[3],k=arguments[4]||0),Na('WebGLRenderer: copyTextureToTexture3D function has been deprecated. Use "copyTextureToTexture" instead.'),this.copyTextureToTexture(w,N,G,Y,k)},this.initRenderTarget=function(w){At.get(w).__webglFramebuffer===void 0&&C.setupRenderTarget(w)},this.initTexture=function(w){w.isCubeTexture?C.setTextureCube(w,0):w.isData3DTexture?C.setTexture3D(w,0):w.isDataArrayTexture||w.isCompressedArrayTexture?C.setTexture2DArray(w,0):C.setTexture2D(w,0),dt.unbindTexture()},this.resetState=function(){A=0,T=0,R=null,dt.reset(),Qt.reset()},typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("observe",{detail:this}))}get coordinateSystem(){return ss}get outputColorSpace(){return this._outputColorSpace}set outputColorSpace(t){this._outputColorSpace=t;let e=this.getContext();e.drawingBufferColorspace=ge._getDrawingBufferColorSpace(t),e.unpackColorSpace=ge._getUnpackColorSpace()}},Uc=class s{constructor(t,e=25e-5){this.isFogExp2=!0,this.name="",this.color=new se(t),this.density=e}clone(){return new s(this.color,this.density)}toJSON(){return{type:"FogExp2",name:this.name,color:this.color.getHex(),density:this.density}}};var Lo=class extends Hn{constructor(){super(),this.isScene=!0,this.type="Scene",this.background=null,this.environment=null,this.fog=null,this.backgroundBlurriness=0,this.backgroundIntensity=1,this.backgroundRotation=new mi,this.environmentIntensity=1,this.environmentRotation=new mi,this.overrideMaterial=null,typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("observe",{detail:this}))}copy(t,e){return super.copy(t,e),t.background!==null&&(this.background=t.background.clone()),t.environment!==null&&(this.environment=t.environment.clone()),t.fog!==null&&(this.fog=t.fog.clone()),this.backgroundBlurriness=t.backgroundBlurriness,this.backgroundIntensity=t.backgroundIntensity,this.backgroundRotation.copy(t.backgroundRotation),this.environmentIntensity=t.environmentIntensity,this.environmentRotation.copy(t.environmentRotation),t.overrideMaterial!==null&&(this.overrideMaterial=t.overrideMaterial.clone()),this.matrixAutoUpdate=t.matrixAutoUpdate,this}toJSON(t){let e=super.toJSON(t);return this.fog!==null&&(e.object.fog=this.fog.toJSON()),this.backgroundBlurriness>0&&(e.object.backgroundBlurriness=this.backgroundBlurriness),this.backgroundIntensity!==1&&(e.object.backgroundIntensity=this.backgroundIntensity),e.object.backgroundRotation=this.backgroundRotation.toArray(),this.environmentIntensity!==1&&(e.object.environmentIntensity=this.environmentIntensity),e.object.environmentRotation=this.environmentRotation.toArray(),e}};var ud=class extends Vn{constructor(t=null,e=1,n=1,i,r,o,a,l,c=jn,h=jn,u,f){super(null,o,a,l,c,h,i,r,u,f),this.isDataTexture=!0,this.image={data:t,width:e,height:n},this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1}};var Er=class extends ti{constructor(t,e,n,i=1){super(t,e,n),this.isInstancedBufferAttribute=!0,this.meshPerAttribute=i}copy(t){return super.copy(t),this.meshPerAttribute=t.meshPerAttribute,this}toJSON(){let t=super.toJSON();return t.meshPerAttribute=this.meshPerAttribute,t.isInstancedBufferAttribute=!0,t}},_o=new Ce,v_=new Ce,uc=[],x_=new as,cw=new Ce,La=new ve,Da=new Sr,Nc=class extends ve{constructor(t,e,n){super(t,e),this.isInstancedMesh=!0,this.instanceMatrix=new Er(new Float32Array(n*16),16),this.instanceColor=null,this.morphTexture=null,this.count=n,this.boundingBox=null,this.boundingSphere=null;for(let i=0;i<n;i++)this.setMatrixAt(i,cw)}computeBoundingBox(){let t=this.geometry,e=this.count;this.boundingBox===null&&(this.boundingBox=new as),t.boundingBox===null&&t.computeBoundingBox(),this.boundingBox.makeEmpty();for(let n=0;n<e;n++)this.getMatrixAt(n,_o),x_.copy(t.boundingBox).applyMatrix4(_o),this.boundingBox.union(x_)}computeBoundingSphere(){let t=this.geometry,e=this.count;this.boundingSphere===null&&(this.boundingSphere=new Sr),t.boundingSphere===null&&t.computeBoundingSphere(),this.boundingSphere.makeEmpty();for(let n=0;n<e;n++)this.getMatrixAt(n,_o),Da.copy(t.boundingSphere).applyMatrix4(_o),this.boundingSphere.union(Da)}copy(t,e){return super.copy(t,e),this.instanceMatrix.copy(t.instanceMatrix),t.morphTexture!==null&&(this.morphTexture=t.morphTexture.clone()),t.instanceColor!==null&&(this.instanceColor=t.instanceColor.clone()),this.count=t.count,t.boundingBox!==null&&(this.boundingBox=t.boundingBox.clone()),t.boundingSphere!==null&&(this.boundingSphere=t.boundingSphere.clone()),this}getColorAt(t,e){e.fromArray(this.instanceColor.array,t*3)}getMatrixAt(t,e){e.fromArray(this.instanceMatrix.array,t*16)}getMorphAt(t,e){let n=e.morphTargetInfluences,i=this.morphTexture.source.data.data,r=n.length+1,o=t*r+1;for(let a=0;a<n.length;a++)n[a]=i[o+a]}raycast(t,e){let n=this.matrixWorld,i=this.count;if(La.geometry=this.geometry,La.material=this.material,La.material!==void 0&&(this.boundingSphere===null&&this.computeBoundingSphere(),Da.copy(this.boundingSphere),Da.applyMatrix4(n),t.ray.intersectsSphere(Da)!==!1))for(let r=0;r<i;r++){this.getMatrixAt(r,_o),v_.multiplyMatrices(n,_o),La.matrixWorld=v_,La.raycast(t,uc);for(let o=0,a=uc.length;o<a;o++){let l=uc[o];l.instanceId=r,l.object=this,e.push(l)}uc.length=0}}setColorAt(t,e){this.instanceColor===null&&(this.instanceColor=new Er(new Float32Array(this.instanceMatrix.count*3).fill(1),3)),e.toArray(this.instanceColor.array,t*3)}setMatrixAt(t,e){e.toArray(this.instanceMatrix.array,t*16)}setMorphAt(t,e){let n=e.morphTargetInfluences,i=n.length+1;this.morphTexture===null&&(this.morphTexture=new ud(new Float32Array(i*this.count),i,this.count,Vd,Bi));let r=this.morphTexture.source.data.data,o=0;for(let c=0;c<n.length;c++)o+=n[c];let a=this.geometry.morphTargetsRelative?1:1-o,l=i*t;r[l]=a,r.set(n,l+1)}updateMorphTargets(){}dispose(){return this.dispatchEvent({type:"dispose"}),this.morphTexture!==null&&(this.morphTexture.dispose(),this.morphTexture=null),this}};var Do=class extends Vn{constructor(t,e,n,i,r,o,a,l,c){super(t,e,n,i,r,o,a,l,c),this.isCanvasTexture=!0,this.needsUpdate=!0}},gi=class{constructor(){this.type="Curve",this.arcLengthDivisions=200}getPoint(){return console.warn("THREE.Curve: .getPoint() not implemented."),null}getPointAt(t,e){let n=this.getUtoTmapping(t);return this.getPoint(n,e)}getPoints(t=5){let e=[];for(let n=0;n<=t;n++)e.push(this.getPoint(n/t));return e}getSpacedPoints(t=5){let e=[];for(let n=0;n<=t;n++)e.push(this.getPointAt(n/t));return e}getLength(){let t=this.getLengths();return t[t.length-1]}getLengths(t=this.arcLengthDivisions){if(this.cacheArcLengths&&this.cacheArcLengths.length===t+1&&!this.needsUpdate)return this.cacheArcLengths;this.needsUpdate=!1;let e=[],n,i=this.getPoint(0),r=0;e.push(0);for(let o=1;o<=t;o++)n=this.getPoint(o/t),r+=n.distanceTo(i),e.push(r),i=n;return this.cacheArcLengths=e,e}updateArcLengths(){this.needsUpdate=!0,this.getLengths()}getUtoTmapping(t,e){let n=this.getLengths(),i=0,r=n.length,o;e?o=e:o=t*n[r-1];let a=0,l=r-1,c;for(;a<=l;)if(i=Math.floor(a+(l-a)/2),c=n[i]-o,c<0)a=i+1;else if(c>0)l=i-1;else{l=i;break}if(i=l,n[i]===o)return i/(r-1);let h=n[i],f=n[i+1]-h,d=(o-h)/f;return(i+d)/(r-1)}getTangent(t,e){let i=t-1e-4,r=t+1e-4;i<0&&(i=0),r>1&&(r=1);let o=this.getPoint(i),a=this.getPoint(r),l=e||(o.isVector2?new vt:new B);return l.copy(a).sub(o).normalize(),l}getTangentAt(t,e){let n=this.getUtoTmapping(t);return this.getTangent(n,e)}computeFrenetFrames(t,e){let n=new B,i=[],r=[],o=[],a=new B,l=new Ce;for(let d=0;d<=t;d++){let g=d/t;i[d]=this.getTangentAt(g,new B)}r[0]=new B,o[0]=new B;let c=Number.MAX_VALUE,h=Math.abs(i[0].x),u=Math.abs(i[0].y),f=Math.abs(i[0].z);h<=c&&(c=h,n.set(1,0,0)),u<=c&&(c=u,n.set(0,1,0)),f<=c&&n.set(0,0,1),a.crossVectors(i[0],n).normalize(),r[0].crossVectors(i[0],a),o[0].crossVectors(i[0],r[0]);for(let d=1;d<=t;d++){if(r[d]=r[d-1].clone(),o[d]=o[d-1].clone(),a.crossVectors(i[d-1],i[d]),a.length()>Number.EPSILON){a.normalize();let g=Math.acos(Sn(i[d-1].dot(i[d]),-1,1));r[d].applyMatrix4(l.makeRotationAxis(a,g))}o[d].crossVectors(i[d],r[d])}if(e===!0){let d=Math.acos(Sn(r[0].dot(r[t]),-1,1));d/=t,i[0].dot(a.crossVectors(r[0],r[t]))>0&&(d=-d);for(let g=1;g<=t;g++)r[g].applyMatrix4(l.makeRotationAxis(i[g],d*g)),o[g].crossVectors(i[g],r[g])}return{tangents:i,normals:r,binormals:o}}clone(){return new this.constructor().copy(this)}copy(t){return this.arcLengthDivisions=t.arcLengthDivisions,this}toJSON(){let t={metadata:{version:4.6,type:"Curve",generator:"Curve.toJSON"}};return t.arcLengthDivisions=this.arcLengthDivisions,t.type=this.type,t}fromJSON(t){return this.arcLengthDivisions=t.arcLengthDivisions,this}},Ha=class extends gi{constructor(t=0,e=0,n=1,i=1,r=0,o=Math.PI*2,a=!1,l=0){super(),this.isEllipseCurve=!0,this.type="EllipseCurve",this.aX=t,this.aY=e,this.xRadius=n,this.yRadius=i,this.aStartAngle=r,this.aEndAngle=o,this.aClockwise=a,this.aRotation=l}getPoint(t,e=new vt){let n=e,i=Math.PI*2,r=this.aEndAngle-this.aStartAngle,o=Math.abs(r)<Number.EPSILON;for(;r<0;)r+=i;for(;r>i;)r-=i;r<Number.EPSILON&&(o?r=0:r=i),this.aClockwise===!0&&!o&&(r===i?r=-i:r=r-i);let a=this.aStartAngle+t*r,l=this.aX+this.xRadius*Math.cos(a),c=this.aY+this.yRadius*Math.sin(a);if(this.aRotation!==0){let h=Math.cos(this.aRotation),u=Math.sin(this.aRotation),f=l-this.aX,d=c-this.aY;l=f*h-d*u+this.aX,c=f*u+d*h+this.aY}return n.set(l,c)}copy(t){return super.copy(t),this.aX=t.aX,this.aY=t.aY,this.xRadius=t.xRadius,this.yRadius=t.yRadius,this.aStartAngle=t.aStartAngle,this.aEndAngle=t.aEndAngle,this.aClockwise=t.aClockwise,this.aRotation=t.aRotation,this}toJSON(){let t=super.toJSON();return t.aX=this.aX,t.aY=this.aY,t.xRadius=this.xRadius,t.yRadius=this.yRadius,t.aStartAngle=this.aStartAngle,t.aEndAngle=this.aEndAngle,t.aClockwise=this.aClockwise,t.aRotation=this.aRotation,t}fromJSON(t){return super.fromJSON(t),this.aX=t.aX,this.aY=t.aY,this.xRadius=t.xRadius,this.yRadius=t.yRadius,this.aStartAngle=t.aStartAngle,this.aEndAngle=t.aEndAngle,this.aClockwise=t.aClockwise,this.aRotation=t.aRotation,this}},fd=class extends Ha{constructor(t,e,n,i,r,o){super(t,e,n,n,i,r,o),this.isArcCurve=!0,this.type="ArcCurve"}};function qd(){let s=0,t=0,e=0,n=0;function i(r,o,a,l){s=r,t=a,e=-3*r+3*o-2*a-l,n=2*r-2*o+a+l}return{initCatmullRom:function(r,o,a,l,c){i(o,a,c*(a-r),c*(l-o))},initNonuniformCatmullRom:function(r,o,a,l,c,h,u){let f=(o-r)/c-(a-r)/(c+h)+(a-o)/h,d=(a-o)/h-(l-o)/(h+u)+(l-a)/u;f*=h,d*=h,i(o,a,f,d)},calc:function(r){let o=r*r,a=o*r;return s+t*r+e*o+n*a}}}var fc=new B,ef=new qd,nf=new qd,sf=new qd,dd=class extends gi{constructor(t=[],e=!1,n="centripetal",i=.5){super(),this.isCatmullRomCurve3=!0,this.type="CatmullRomCurve3",this.points=t,this.closed=e,this.curveType=n,this.tension=i}getPoint(t,e=new B){let n=e,i=this.points,r=i.length,o=(r-(this.closed?0:1))*t,a=Math.floor(o),l=o-a;this.closed?a+=a>0?0:(Math.floor(Math.abs(a)/r)+1)*r:l===0&&a===r-1&&(a=r-2,l=1);let c,h;this.closed||a>0?c=i[(a-1)%r]:(fc.subVectors(i[0],i[1]).add(i[0]),c=fc);let u=i[a%r],f=i[(a+1)%r];if(this.closed||a+2<r?h=i[(a+2)%r]:(fc.subVectors(i[r-1],i[r-2]).add(i[r-1]),h=fc),this.curveType==="centripetal"||this.curveType==="chordal"){let d=this.curveType==="chordal"?.5:.25,g=Math.pow(c.distanceToSquared(u),d),_=Math.pow(u.distanceToSquared(f),d),m=Math.pow(f.distanceToSquared(h),d);_<1e-4&&(_=1),g<1e-4&&(g=_),m<1e-4&&(m=_),ef.initNonuniformCatmullRom(c.x,u.x,f.x,h.x,g,_,m),nf.initNonuniformCatmullRom(c.y,u.y,f.y,h.y,g,_,m),sf.initNonuniformCatmullRom(c.z,u.z,f.z,h.z,g,_,m)}else this.curveType==="catmullrom"&&(ef.initCatmullRom(c.x,u.x,f.x,h.x,this.tension),nf.initCatmullRom(c.y,u.y,f.y,h.y,this.tension),sf.initCatmullRom(c.z,u.z,f.z,h.z,this.tension));return n.set(ef.calc(l),nf.calc(l),sf.calc(l)),n}copy(t){super.copy(t),this.points=[];for(let e=0,n=t.points.length;e<n;e++){let i=t.points[e];this.points.push(i.clone())}return this.closed=t.closed,this.curveType=t.curveType,this.tension=t.tension,this}toJSON(){let t=super.toJSON();t.points=[];for(let e=0,n=this.points.length;e<n;e++){let i=this.points[e];t.points.push(i.toArray())}return t.closed=this.closed,t.curveType=this.curveType,t.tension=this.tension,t}fromJSON(t){super.fromJSON(t),this.points=[];for(let e=0,n=t.points.length;e<n;e++){let i=t.points[e];this.points.push(new B().fromArray(i))}return this.closed=t.closed,this.curveType=t.curveType,this.tension=t.tension,this}};function y_(s,t,e,n,i){let r=(n-t)*.5,o=(i-e)*.5,a=s*s,l=s*a;return(2*e-2*n+r+o)*l+(-3*e+3*n-2*r-o)*a+r*s+e}function hw(s,t){let e=1-s;return e*e*t}function uw(s,t){return 2*(1-s)*s*t}function fw(s,t){return s*s*t}function Ba(s,t,e,n){return hw(s,t)+uw(s,e)+fw(s,n)}function dw(s,t){let e=1-s;return e*e*e*t}function pw(s,t){let e=1-s;return 3*e*e*s*t}function mw(s,t){return 3*(1-s)*s*s*t}function gw(s,t){return s*s*s*t}function ka(s,t,e,n,i){return dw(s,t)+pw(s,e)+mw(s,n)+gw(s,i)}var Oc=class extends gi{constructor(t=new vt,e=new vt,n=new vt,i=new vt){super(),this.isCubicBezierCurve=!0,this.type="CubicBezierCurve",this.v0=t,this.v1=e,this.v2=n,this.v3=i}getPoint(t,e=new vt){let n=e,i=this.v0,r=this.v1,o=this.v2,a=this.v3;return n.set(ka(t,i.x,r.x,o.x,a.x),ka(t,i.y,r.y,o.y,a.y)),n}copy(t){return super.copy(t),this.v0.copy(t.v0),this.v1.copy(t.v1),this.v2.copy(t.v2),this.v3.copy(t.v3),this}toJSON(){let t=super.toJSON();return t.v0=this.v0.toArray(),t.v1=this.v1.toArray(),t.v2=this.v2.toArray(),t.v3=this.v3.toArray(),t}fromJSON(t){return super.fromJSON(t),this.v0.fromArray(t.v0),this.v1.fromArray(t.v1),this.v2.fromArray(t.v2),this.v3.fromArray(t.v3),this}},pd=class extends gi{constructor(t=new B,e=new B,n=new B,i=new B){super(),this.isCubicBezierCurve3=!0,this.type="CubicBezierCurve3",this.v0=t,this.v1=e,this.v2=n,this.v3=i}getPoint(t,e=new B){let n=e,i=this.v0,r=this.v1,o=this.v2,a=this.v3;return n.set(ka(t,i.x,r.x,o.x,a.x),ka(t,i.y,r.y,o.y,a.y),ka(t,i.z,r.z,o.z,a.z)),n}copy(t){return super.copy(t),this.v0.copy(t.v0),this.v1.copy(t.v1),this.v2.copy(t.v2),this.v3.copy(t.v3),this}toJSON(){let t=super.toJSON();return t.v0=this.v0.toArray(),t.v1=this.v1.toArray(),t.v2=this.v2.toArray(),t.v3=this.v3.toArray(),t}fromJSON(t){return super.fromJSON(t),this.v0.fromArray(t.v0),this.v1.fromArray(t.v1),this.v2.fromArray(t.v2),this.v3.fromArray(t.v3),this}},Fc=class extends gi{constructor(t=new vt,e=new vt){super(),this.isLineCurve=!0,this.type="LineCurve",this.v1=t,this.v2=e}getPoint(t,e=new vt){let n=e;return t===1?n.copy(this.v2):(n.copy(this.v2).sub(this.v1),n.multiplyScalar(t).add(this.v1)),n}getPointAt(t,e){return this.getPoint(t,e)}getTangent(t,e=new vt){return e.subVectors(this.v2,this.v1).normalize()}getTangentAt(t,e){return this.getTangent(t,e)}copy(t){return super.copy(t),this.v1.copy(t.v1),this.v2.copy(t.v2),this}toJSON(){let t=super.toJSON();return t.v1=this.v1.toArray(),t.v2=this.v2.toArray(),t}fromJSON(t){return super.fromJSON(t),this.v1.fromArray(t.v1),this.v2.fromArray(t.v2),this}},md=class extends gi{constructor(t=new B,e=new B){super(),this.isLineCurve3=!0,this.type="LineCurve3",this.v1=t,this.v2=e}getPoint(t,e=new B){let n=e;return t===1?n.copy(this.v2):(n.copy(this.v2).sub(this.v1),n.multiplyScalar(t).add(this.v1)),n}getPointAt(t,e){return this.getPoint(t,e)}getTangent(t,e=new B){return e.subVectors(this.v2,this.v1).normalize()}getTangentAt(t,e){return this.getTangent(t,e)}copy(t){return super.copy(t),this.v1.copy(t.v1),this.v2.copy(t.v2),this}toJSON(){let t=super.toJSON();return t.v1=this.v1.toArray(),t.v2=this.v2.toArray(),t}fromJSON(t){return super.fromJSON(t),this.v1.fromArray(t.v1),this.v2.fromArray(t.v2),this}},Bc=class extends gi{constructor(t=new vt,e=new vt,n=new vt){super(),this.isQuadraticBezierCurve=!0,this.type="QuadraticBezierCurve",this.v0=t,this.v1=e,this.v2=n}getPoint(t,e=new vt){let n=e,i=this.v0,r=this.v1,o=this.v2;return n.set(Ba(t,i.x,r.x,o.x),Ba(t,i.y,r.y,o.y)),n}copy(t){return super.copy(t),this.v0.copy(t.v0),this.v1.copy(t.v1),this.v2.copy(t.v2),this}toJSON(){let t=super.toJSON();return t.v0=this.v0.toArray(),t.v1=this.v1.toArray(),t.v2=this.v2.toArray(),t}fromJSON(t){return super.fromJSON(t),this.v0.fromArray(t.v0),this.v1.fromArray(t.v1),this.v2.fromArray(t.v2),this}},gd=class extends gi{constructor(t=new B,e=new B,n=new B){super(),this.isQuadraticBezierCurve3=!0,this.type="QuadraticBezierCurve3",this.v0=t,this.v1=e,this.v2=n}getPoint(t,e=new B){let n=e,i=this.v0,r=this.v1,o=this.v2;return n.set(Ba(t,i.x,r.x,o.x),Ba(t,i.y,r.y,o.y),Ba(t,i.z,r.z,o.z)),n}copy(t){return super.copy(t),this.v0.copy(t.v0),this.v1.copy(t.v1),this.v2.copy(t.v2),this}toJSON(){let t=super.toJSON();return t.v0=this.v0.toArray(),t.v1=this.v1.toArray(),t.v2=this.v2.toArray(),t}fromJSON(t){return super.fromJSON(t),this.v0.fromArray(t.v0),this.v1.fromArray(t.v1),this.v2.fromArray(t.v2),this}},kc=class extends gi{constructor(t=[]){super(),this.isSplineCurve=!0,this.type="SplineCurve",this.points=t}getPoint(t,e=new vt){let n=e,i=this.points,r=(i.length-1)*t,o=Math.floor(r),a=r-o,l=i[o===0?o:o-1],c=i[o],h=i[o>i.length-2?i.length-1:o+1],u=i[o>i.length-3?i.length-1:o+2];return n.set(y_(a,l.x,c.x,h.x,u.x),y_(a,l.y,c.y,h.y,u.y)),n}copy(t){super.copy(t),this.points=[];for(let e=0,n=t.points.length;e<n;e++){let i=t.points[e];this.points.push(i.clone())}return this}toJSON(){let t=super.toJSON();t.points=[];for(let e=0,n=this.points.length;e<n;e++){let i=this.points[e];t.points.push(i.toArray())}return t}fromJSON(t){super.fromJSON(t),this.points=[];for(let e=0,n=t.points.length;e<n;e++){let i=t.points[e];this.points.push(new vt().fromArray(i))}return this}},_d=Object.freeze({__proto__:null,ArcCurve:fd,CatmullRomCurve3:dd,CubicBezierCurve:Oc,CubicBezierCurve3:pd,EllipseCurve:Ha,LineCurve:Fc,LineCurve3:md,QuadraticBezierCurve:Bc,QuadraticBezierCurve3:gd,SplineCurve:kc}),vd=class extends gi{constructor(){super(),this.type="CurvePath",this.curves=[],this.autoClose=!1}add(t){this.curves.push(t)}closePath(){let t=this.curves[0].getPoint(0),e=this.curves[this.curves.length-1].getPoint(1);if(!t.equals(e)){let n=t.isVector2===!0?"LineCurve":"LineCurve3";this.curves.push(new _d[n](e,t))}return this}getPoint(t,e){let n=t*this.getLength(),i=this.getCurveLengths(),r=0;for(;r<i.length;){if(i[r]>=n){let o=i[r]-n,a=this.curves[r],l=a.getLength(),c=l===0?0:1-o/l;return a.getPointAt(c,e)}r++}return null}getLength(){let t=this.getCurveLengths();return t[t.length-1]}updateArcLengths(){this.needsUpdate=!0,this.cacheLengths=null,this.getCurveLengths()}getCurveLengths(){if(this.cacheLengths&&this.cacheLengths.length===this.curves.length)return this.cacheLengths;let t=[],e=0;for(let n=0,i=this.curves.length;n<i;n++)e+=this.curves[n].getLength(),t.push(e);return this.cacheLengths=t,t}getSpacedPoints(t=40){let e=[];for(let n=0;n<=t;n++)e.push(this.getPoint(n/t));return this.autoClose&&e.push(e[0]),e}getPoints(t=12){let e=[],n;for(let i=0,r=this.curves;i<r.length;i++){let o=r[i],a=o.isEllipseCurve?t*2:o.isLineCurve||o.isLineCurve3?1:o.isSplineCurve?t*o.points.length:t,l=o.getPoints(a);for(let c=0;c<l.length;c++){let h=l[c];n&&n.equals(h)||(e.push(h),n=h)}}return this.autoClose&&e.length>1&&!e[e.length-1].equals(e[0])&&e.push(e[0]),e}copy(t){super.copy(t),this.curves=[];for(let e=0,n=t.curves.length;e<n;e++){let i=t.curves[e];this.curves.push(i.clone())}return this.autoClose=t.autoClose,this}toJSON(){let t=super.toJSON();t.autoClose=this.autoClose,t.curves=[];for(let e=0,n=this.curves.length;e<n;e++){let i=this.curves[e];t.curves.push(i.toJSON())}return t}fromJSON(t){super.fromJSON(t),this.autoClose=t.autoClose,this.curves=[];for(let e=0,n=t.curves.length;e<n;e++){let i=t.curves[e];this.curves.push(new _d[i.type]().fromJSON(i))}return this}},zc=class extends vd{constructor(t){super(),this.type="Path",this.currentPoint=new vt,t&&this.setFromPoints(t)}setFromPoints(t){this.moveTo(t[0].x,t[0].y);for(let e=1,n=t.length;e<n;e++)this.lineTo(t[e].x,t[e].y);return this}moveTo(t,e){return this.currentPoint.set(t,e),this}lineTo(t,e){let n=new Fc(this.currentPoint.clone(),new vt(t,e));return this.curves.push(n),this.currentPoint.set(t,e),this}quadraticCurveTo(t,e,n,i){let r=new Bc(this.currentPoint.clone(),new vt(t,e),new vt(n,i));return this.curves.push(r),this.currentPoint.set(n,i),this}bezierCurveTo(t,e,n,i,r,o){let a=new Oc(this.currentPoint.clone(),new vt(t,e),new vt(n,i),new vt(r,o));return this.curves.push(a),this.currentPoint.set(r,o),this}splineThru(t){let e=[this.currentPoint.clone()].concat(t),n=new kc(e);return this.curves.push(n),this.currentPoint.copy(t[t.length-1]),this}arc(t,e,n,i,r,o){let a=this.currentPoint.x,l=this.currentPoint.y;return this.absarc(t+a,e+l,n,i,r,o),this}absarc(t,e,n,i,r,o){return this.absellipse(t,e,n,n,i,r,o),this}ellipse(t,e,n,i,r,o,a,l){let c=this.currentPoint.x,h=this.currentPoint.y;return this.absellipse(t+c,e+h,n,i,r,o,a,l),this}absellipse(t,e,n,i,r,o,a,l){let c=new Ha(t,e,n,i,r,o,a,l);if(this.curves.length>0){let u=c.getPoint(0);u.equals(this.currentPoint)||this.lineTo(u.x,u.y)}this.curves.push(c);let h=c.getPoint(1);return this.currentPoint.copy(h),this}copy(t){return super.copy(t),this.currentPoint.copy(t.currentPoint),this}toJSON(){let t=super.toJSON();return t.currentPoint=this.currentPoint.toArray(),t}fromJSON(t){return super.fromJSON(t),this.currentPoint.fromArray(t.currentPoint),this}};var Ar=class extends zc{constructor(t){super(t),this.uuid=Fo(),this.type="Shape",this.holes=[]}getPointsHoles(t){let e=[];for(let n=0,i=this.holes.length;n<i;n++)e[n]=this.holes[n].getPoints(t);return e}extractPoints(t){return{shape:this.getPoints(t),holes:this.getPointsHoles(t)}}copy(t){super.copy(t),this.holes=[];for(let e=0,n=t.holes.length;e<n;e++){let i=t.holes[e];this.holes.push(i.clone())}return this}toJSON(){let t=super.toJSON();t.uuid=this.uuid,t.holes=[];for(let e=0,n=this.holes.length;e<n;e++){let i=this.holes[e];t.holes.push(i.toJSON())}return t}fromJSON(t){super.fromJSON(t),this.uuid=t.uuid,this.holes=[];for(let e=0,n=t.holes.length;e<n;e++){let i=t.holes[e];this.holes.push(new zc().fromJSON(i))}return this}},_w={triangulate:function(s,t,e=2){let n=t&&t.length,i=n?t[0]*e:s.length,r=J_(s,0,i,e,!0),o=[];if(!r||r.next===r.prev)return o;let a,l,c,h,u,f,d;if(n&&(r=Sw(s,t,r,e)),s.length>80*e){a=c=s[0],l=h=s[1];for(let g=e;g<i;g+=e)u=s[g],f=s[g+1],u<a&&(a=u),f<l&&(l=f),u>c&&(c=u),f>h&&(h=f);d=Math.max(c-a,h-l),d=d!==0?32767/d:0}return Ga(r,o,e,a,l,d,0),o}};function J_(s,t,e,n,i){let r,o;if(i===Dw(s,t,e,n)>0)for(r=t;r<e;r+=n)o=M_(r,s[r],s[r+1],o);else for(r=e-n;r>=t;r-=n)o=M_(r,s[r],s[r+1],o);return o&&Kc(o,o.next)&&(Xa(o),o=o.next),o}function Cr(s,t){if(!s)return s;t||(t=s);let e=s,n;do if(n=!1,!e.steiner&&(Kc(e,e.next)||Ve(e.prev,e,e.next)===0)){if(Xa(e),e=t=e.prev,e===e.next)break;n=!0}else e=e.next;while(n||e!==t);return t}function Ga(s,t,e,n,i,r,o){if(!s)return;!o&&r&&Aw(s,n,i,r);let a=s,l,c;for(;s.prev!==s.next;){if(l=s.prev,c=s.next,r?xw(s,n,i,r):vw(s)){t.push(l.i/e|0),t.push(s.i/e|0),t.push(c.i/e|0),Xa(s),s=c.next,a=c.next;continue}if(s=c,s===a){o?o===1?(s=yw(Cr(s),t,e),Ga(s,t,e,n,i,r,2)):o===2&&Mw(s,t,e,n,i,r):Ga(Cr(s),t,e,n,i,r,1);break}}}function vw(s){let t=s.prev,e=s,n=s.next;if(Ve(t,e,n)>=0)return!1;let i=t.x,r=e.x,o=n.x,a=t.y,l=e.y,c=n.y,h=i<r?i<o?i:o:r<o?r:o,u=a<l?a<c?a:c:l<c?l:c,f=i>r?i>o?i:o:r>o?r:o,d=a>l?a>c?a:c:l>c?l:c,g=n.next;for(;g!==t;){if(g.x>=h&&g.x<=f&&g.y>=u&&g.y<=d&&xo(i,a,r,l,o,c,g.x,g.y)&&Ve(g.prev,g,g.next)>=0)return!1;g=g.next}return!0}function xw(s,t,e,n){let i=s.prev,r=s,o=s.next;if(Ve(i,r,o)>=0)return!1;let a=i.x,l=r.x,c=o.x,h=i.y,u=r.y,f=o.y,d=a<l?a<c?a:c:l<c?l:c,g=h<u?h<f?h:f:u<f?u:f,_=a>l?a>c?a:c:l>c?l:c,m=h>u?h>f?h:f:u>f?u:f,p=xd(d,g,t,e,n),S=xd(_,m,t,e,n),y=s.prevZ,v=s.nextZ;for(;y&&y.z>=p&&v&&v.z<=S;){if(y.x>=d&&y.x<=_&&y.y>=g&&y.y<=m&&y!==i&&y!==o&&xo(a,h,l,u,c,f,y.x,y.y)&&Ve(y.prev,y,y.next)>=0||(y=y.prevZ,v.x>=d&&v.x<=_&&v.y>=g&&v.y<=m&&v!==i&&v!==o&&xo(a,h,l,u,c,f,v.x,v.y)&&Ve(v.prev,v,v.next)>=0))return!1;v=v.nextZ}for(;y&&y.z>=p;){if(y.x>=d&&y.x<=_&&y.y>=g&&y.y<=m&&y!==i&&y!==o&&xo(a,h,l,u,c,f,y.x,y.y)&&Ve(y.prev,y,y.next)>=0)return!1;y=y.prevZ}for(;v&&v.z<=S;){if(v.x>=d&&v.x<=_&&v.y>=g&&v.y<=m&&v!==i&&v!==o&&xo(a,h,l,u,c,f,v.x,v.y)&&Ve(v.prev,v,v.next)>=0)return!1;v=v.nextZ}return!0}function yw(s,t,e){let n=s;do{let i=n.prev,r=n.next.next;!Kc(i,r)&&K_(i,n,n.next,r)&&Wa(i,r)&&Wa(r,i)&&(t.push(i.i/e|0),t.push(n.i/e|0),t.push(r.i/e|0),Xa(n),Xa(n.next),n=s=r),n=n.next}while(n!==s);return Cr(n)}function Mw(s,t,e,n,i,r){let o=s;do{let a=o.next.next;for(;a!==o.prev;){if(o.i!==a.i&&Pw(o,a)){let l=Q_(o,a);o=Cr(o,o.next),l=Cr(l,l.next),Ga(o,t,e,n,i,r,0),Ga(l,t,e,n,i,r,0);return}a=a.next}o=o.next}while(o!==s)}function Sw(s,t,e,n){let i=[],r,o,a,l,c;for(r=0,o=t.length;r<o;r++)a=t[r]*n,l=r<o-1?t[r+1]*n:s.length,c=J_(s,a,l,n,!1),c===c.next&&(c.steiner=!0),i.push(Rw(c));for(i.sort(bw),r=0;r<i.length;r++)e=ww(i[r],e);return e}function bw(s,t){return s.x-t.x}function ww(s,t){let e=Tw(s,t);if(!e)return t;let n=Q_(e,s);return Cr(n,n.next),Cr(e,e.next)}function Tw(s,t){let e=t,n=-1/0,i,r=s.x,o=s.y;do{if(o<=e.y&&o>=e.next.y&&e.next.y!==e.y){let f=e.x+(o-e.y)*(e.next.x-e.x)/(e.next.y-e.y);if(f<=r&&f>n&&(n=f,i=e.x<e.next.x?e:e.next,f===r))return i}e=e.next}while(e!==t);if(!i)return null;let a=i,l=i.x,c=i.y,h=1/0,u;e=i;do r>=e.x&&e.x>=l&&r!==e.x&&xo(o<c?r:n,o,l,c,o<c?n:r,o,e.x,e.y)&&(u=Math.abs(o-e.y)/(r-e.x),Wa(e,s)&&(u<h||u===h&&(e.x>i.x||e.x===i.x&&Ew(i,e)))&&(i=e,h=u)),e=e.next;while(e!==a);return i}function Ew(s,t){return Ve(s.prev,s,t.prev)<0&&Ve(t.next,s,s.next)<0}function Aw(s,t,e,n){let i=s;do i.z===0&&(i.z=xd(i.x,i.y,t,e,n)),i.prevZ=i.prev,i.nextZ=i.next,i=i.next;while(i!==s);i.prevZ.nextZ=null,i.prevZ=null,Cw(i)}function Cw(s){let t,e,n,i,r,o,a,l,c=1;do{for(e=s,s=null,r=null,o=0;e;){for(o++,n=e,a=0,t=0;t<c&&(a++,n=n.nextZ,!!n);t++);for(l=c;a>0||l>0&&n;)a!==0&&(l===0||!n||e.z<=n.z)?(i=e,e=e.nextZ,a--):(i=n,n=n.nextZ,l--),r?r.nextZ=i:s=i,i.prevZ=r,r=i;e=n}r.nextZ=null,c*=2}while(o>1);return s}function xd(s,t,e,n,i){return s=(s-e)*i|0,t=(t-n)*i|0,s=(s|s<<8)&16711935,s=(s|s<<4)&252645135,s=(s|s<<2)&858993459,s=(s|s<<1)&1431655765,t=(t|t<<8)&16711935,t=(t|t<<4)&252645135,t=(t|t<<2)&858993459,t=(t|t<<1)&1431655765,s|t<<1}function Rw(s){let t=s,e=s;do(t.x<e.x||t.x===e.x&&t.y<e.y)&&(e=t),t=t.next;while(t!==s);return e}function xo(s,t,e,n,i,r,o,a){return(i-o)*(t-a)>=(s-o)*(r-a)&&(s-o)*(n-a)>=(e-o)*(t-a)&&(e-o)*(r-a)>=(i-o)*(n-a)}function Pw(s,t){return s.next.i!==t.i&&s.prev.i!==t.i&&!Iw(s,t)&&(Wa(s,t)&&Wa(t,s)&&Lw(s,t)&&(Ve(s.prev,s,t.prev)||Ve(s,t.prev,t))||Kc(s,t)&&Ve(s.prev,s,s.next)>0&&Ve(t.prev,t,t.next)>0)}function Ve(s,t,e){return(t.y-s.y)*(e.x-t.x)-(t.x-s.x)*(e.y-t.y)}function Kc(s,t){return s.x===t.x&&s.y===t.y}function K_(s,t,e,n){let i=pc(Ve(s,t,e)),r=pc(Ve(s,t,n)),o=pc(Ve(e,n,s)),a=pc(Ve(e,n,t));return!!(i!==r&&o!==a||i===0&&dc(s,e,t)||r===0&&dc(s,n,t)||o===0&&dc(e,s,n)||a===0&&dc(e,t,n))}function dc(s,t,e){return t.x<=Math.max(s.x,e.x)&&t.x>=Math.min(s.x,e.x)&&t.y<=Math.max(s.y,e.y)&&t.y>=Math.min(s.y,e.y)}function pc(s){return s>0?1:s<0?-1:0}function Iw(s,t){let e=s;do{if(e.i!==s.i&&e.next.i!==s.i&&e.i!==t.i&&e.next.i!==t.i&&K_(e,e.next,s,t))return!0;e=e.next}while(e!==s);return!1}function Wa(s,t){return Ve(s.prev,s,s.next)<0?Ve(s,t,s.next)>=0&&Ve(s,s.prev,t)>=0:Ve(s,t,s.prev)<0||Ve(s,s.next,t)<0}function Lw(s,t){let e=s,n=!1,i=(s.x+t.x)/2,r=(s.y+t.y)/2;do e.y>r!=e.next.y>r&&e.next.y!==e.y&&i<(e.next.x-e.x)*(r-e.y)/(e.next.y-e.y)+e.x&&(n=!n),e=e.next;while(e!==s);return n}function Q_(s,t){let e=new yd(s.i,s.x,s.y),n=new yd(t.i,t.x,t.y),i=s.next,r=t.prev;return s.next=t,t.prev=s,e.next=i,i.prev=e,n.next=e,e.prev=n,r.next=n,n.prev=r,n}function M_(s,t,e,n){let i=new yd(s,t,e);return n?(i.next=n.next,i.prev=n,n.next.prev=i,n.next=i):(i.prev=i,i.next=i),i}function Xa(s){s.next.prev=s.prev,s.prev.next=s.next,s.prevZ&&(s.prevZ.nextZ=s.nextZ),s.nextZ&&(s.nextZ.prevZ=s.prevZ)}function yd(s,t,e){this.i=s,this.x=t,this.y=e,this.prev=null,this.next=null,this.z=0,this.prevZ=null,this.nextZ=null,this.steiner=!1}function Dw(s,t,e,n){let i=0;for(let r=t,o=e-n;r<e;r+=n)i+=(s[o]-s[r])*(s[r+1]+s[o+1]),o=r;return i}var Fs=class s{static area(t){let e=t.length,n=0;for(let i=e-1,r=0;r<e;i=r++)n+=t[i].x*t[r].y-t[r].x*t[i].y;return n*.5}static isClockWise(t){return s.area(t)<0}static triangulateShape(t,e){let n=[],i=[],r=[];S_(t),b_(n,t);let o=t.length;e.forEach(S_);for(let l=0;l<e.length;l++)i.push(o),o+=e[l].length,b_(n,e[l]);let a=_w.triangulate(n,i);for(let l=0;l<a.length;l+=3)r.push(a.slice(l,l+3));return r}};function S_(s){let t=s.length;t>2&&s[t-1].equals(s[0])&&s.pop()}function b_(s,t){for(let e=0;e<t.length;e++)s.push(t[e].x),s.push(t[e].y)}var Vc=class s extends Ei{constructor(t=new Ar([new vt(.5,.5),new vt(-.5,.5),new vt(-.5,-.5),new vt(.5,-.5)]),e={}){super(),this.type="ExtrudeGeometry",this.parameters={shapes:t,options:e},t=Array.isArray(t)?t:[t];let n=this,i=[],r=[];for(let a=0,l=t.length;a<l;a++){let c=t[a];o(c)}this.setAttribute("position",new hn(i,3)),this.setAttribute("uv",new hn(r,2)),this.computeVertexNormals();function o(a){let l=[],c=e.curveSegments!==void 0?e.curveSegments:12,h=e.steps!==void 0?e.steps:1,u=e.depth!==void 0?e.depth:1,f=e.bevelEnabled!==void 0?e.bevelEnabled:!0,d=e.bevelThickness!==void 0?e.bevelThickness:.2,g=e.bevelSize!==void 0?e.bevelSize:d-.1,_=e.bevelOffset!==void 0?e.bevelOffset:0,m=e.bevelSegments!==void 0?e.bevelSegments:3,p=e.extrudePath,S=e.UVGenerator!==void 0?e.UVGenerator:Uw,y,v=!1,E,A,T,R;p&&(y=p.getSpacedPoints(h),v=!0,f=!1,E=p.computeFrenetFrames(h,!1),A=new B,T=new B,R=new B),f||(m=0,d=0,g=0,_=0);let M=a.extractPoints(c),x=M.shape,L=M.holes;if(!Fs.isClockWise(x)){x=x.reverse();for(let et=0,nt=L.length;et<nt;et++){let P=L[et];Fs.isClockWise(P)&&(L[et]=P.reverse())}}let F=Fs.triangulateShape(x,L),z=x;for(let et=0,nt=L.length;et<nt;et++){let P=L[et];x=x.concat(P)}function q(et,nt,P){return nt||console.error("THREE.ExtrudeGeometry: vec does not exist"),et.clone().addScaledVector(nt,P)}let H=x.length,W=F.length;function V(et,nt,P){let It,lt,O,dt=et.x-nt.x,zt=et.y-nt.y,At=P.x-et.x,C=P.y-et.y,b=dt*dt+zt*zt,X=dt*C-zt*At;if(Math.abs(X)>Number.EPSILON){let Q=Math.sqrt(b),it=Math.sqrt(At*At+C*C),j=nt.x-zt/Q,xt=nt.y+dt/Q,pt=P.x-C/it,bt=P.y+At/it,Kt=((pt-j)*C-(bt-xt)*At)/(dt*C-zt*At);It=j+dt*Kt-et.x,lt=xt+zt*Kt-et.y;let ut=It*It+lt*lt;if(ut<=2)return new vt(It,lt);O=Math.sqrt(ut/2)}else{let Q=!1;dt>Number.EPSILON?At>Number.EPSILON&&(Q=!0):dt<-Number.EPSILON?At<-Number.EPSILON&&(Q=!0):Math.sign(zt)===Math.sign(C)&&(Q=!0),Q?(It=-zt,lt=dt,O=Math.sqrt(b)):(It=dt,lt=zt,O=Math.sqrt(b/2))}return new vt(It/O,lt/O)}let st=[];for(let et=0,nt=z.length,P=nt-1,It=et+1;et<nt;et++,P++,It++)P===nt&&(P=0),It===nt&&(It=0),st[et]=V(z[et],z[P],z[It]);let I=[],at,Dt=st.concat();for(let et=0,nt=L.length;et<nt;et++){let P=L[et];at=[];for(let It=0,lt=P.length,O=lt-1,dt=It+1;It<lt;It++,O++,dt++)O===lt&&(O=0),dt===lt&&(dt=0),at[It]=V(P[It],P[O],P[dt]);I.push(at),Dt=Dt.concat(at)}for(let et=0;et<m;et++){let nt=et/m,P=d*Math.cos(nt*Math.PI/2),It=g*Math.sin(nt*Math.PI/2)+_;for(let lt=0,O=z.length;lt<O;lt++){let dt=q(z[lt],st[lt],It);ot(dt.x,dt.y,-P)}for(let lt=0,O=L.length;lt<O;lt++){let dt=L[lt];at=I[lt];for(let zt=0,At=dt.length;zt<At;zt++){let C=q(dt[zt],at[zt],It);ot(C.x,C.y,-P)}}}let Vt=g+_;for(let et=0;et<H;et++){let nt=f?q(x[et],Dt[et],Vt):x[et];v?(T.copy(E.normals[0]).multiplyScalar(nt.x),A.copy(E.binormals[0]).multiplyScalar(nt.y),R.copy(y[0]).add(T).add(A),ot(R.x,R.y,R.z)):ot(nt.x,nt.y,0)}for(let et=1;et<=h;et++)for(let nt=0;nt<H;nt++){let P=f?q(x[nt],Dt[nt],Vt):x[nt];v?(T.copy(E.normals[et]).multiplyScalar(P.x),A.copy(E.binormals[et]).multiplyScalar(P.y),R.copy(y[et]).add(T).add(A),ot(R.x,R.y,R.z)):ot(P.x,P.y,u/h*et)}for(let et=m-1;et>=0;et--){let nt=et/m,P=d*Math.cos(nt*Math.PI/2),It=g*Math.sin(nt*Math.PI/2)+_;for(let lt=0,O=z.length;lt<O;lt++){let dt=q(z[lt],st[lt],It);ot(dt.x,dt.y,u+P)}for(let lt=0,O=L.length;lt<O;lt++){let dt=L[lt];at=I[lt];for(let zt=0,At=dt.length;zt<At;zt++){let C=q(dt[zt],at[zt],It);v?ot(C.x,C.y+y[h-1].y,y[h-1].x+P):ot(C.x,C.y,u+P)}}}Z(),rt();function Z(){let et=i.length/3;if(f){let nt=0,P=H*nt;for(let It=0;It<W;It++){let lt=F[It];Rt(lt[2]+P,lt[1]+P,lt[0]+P)}nt=h+m*2,P=H*nt;for(let It=0;It<W;It++){let lt=F[It];Rt(lt[0]+P,lt[1]+P,lt[2]+P)}}else{for(let nt=0;nt<W;nt++){let P=F[nt];Rt(P[2],P[1],P[0])}for(let nt=0;nt<W;nt++){let P=F[nt];Rt(P[0]+H*h,P[1]+H*h,P[2]+H*h)}}n.addGroup(et,i.length/3-et,0)}function rt(){let et=i.length/3,nt=0;St(z,nt),nt+=z.length;for(let P=0,It=L.length;P<It;P++){let lt=L[P];St(lt,nt),nt+=lt.length}n.addGroup(et,i.length/3-et,1)}function St(et,nt){let P=et.length;for(;--P>=0;){let It=P,lt=P-1;lt<0&&(lt=et.length-1);for(let O=0,dt=h+m*2;O<dt;O++){let zt=H*O,At=H*(O+1),C=nt+It+zt,b=nt+lt+zt,X=nt+lt+At,Q=nt+It+At;Bt(C,b,X,Q)}}}function ot(et,nt,P){l.push(et),l.push(nt),l.push(P)}function Rt(et,nt,P){Wt(et),Wt(nt),Wt(P);let It=i.length/3,lt=S.generateTopUV(n,i,It-3,It-2,It-1);Xt(lt[0]),Xt(lt[1]),Xt(lt[2])}function Bt(et,nt,P,It){Wt(et),Wt(nt),Wt(It),Wt(nt),Wt(P),Wt(It);let lt=i.length/3,O=S.generateSideWallUV(n,i,lt-6,lt-3,lt-2,lt-1);Xt(O[0]),Xt(O[1]),Xt(O[3]),Xt(O[1]),Xt(O[2]),Xt(O[3])}function Wt(et){i.push(l[et*3+0]),i.push(l[et*3+1]),i.push(l[et*3+2])}function Xt(et){r.push(et.x),r.push(et.y)}}}copy(t){return super.copy(t),this.parameters=Object.assign({},t.parameters),this}toJSON(){let t=super.toJSON(),e=this.parameters.shapes,n=this.parameters.options;return Nw(e,n,t)}static fromJSON(t,e){let n=[];for(let r=0,o=t.shapes.length;r<o;r++){let a=e[t.shapes[r]];n.push(a)}let i=t.options.extrudePath;return i!==void 0&&(t.options.extrudePath=new _d[i.type]().fromJSON(i)),new s(n,t.options)}},Uw={generateTopUV:function(s,t,e,n,i){let r=t[e*3],o=t[e*3+1],a=t[n*3],l=t[n*3+1],c=t[i*3],h=t[i*3+1];return[new vt(r,o),new vt(a,l),new vt(c,h)]},generateSideWallUV:function(s,t,e,n,i,r){let o=t[e*3],a=t[e*3+1],l=t[e*3+2],c=t[n*3],h=t[n*3+1],u=t[n*3+2],f=t[i*3],d=t[i*3+1],g=t[i*3+2],_=t[r*3],m=t[r*3+1],p=t[r*3+2];return Math.abs(a-h)<Math.abs(o-c)?[new vt(o,1-l),new vt(c,1-u),new vt(f,1-g),new vt(_,1-p)]:[new vt(a,1-l),new vt(h,1-u),new vt(d,1-g),new vt(m,1-p)]}};function Nw(s,t,e){if(e.shapes=[],Array.isArray(s))for(let n=0,i=s.length;n<i;n++){let r=s[n];e.shapes.push(r.uuid)}else e.shapes.push(s.uuid);return e.options=Object.assign({},t),t.extrudePath!==void 0&&(e.options.extrudePath=t.extrudePath.toJSON()),e}var Ya=class s extends Ei{constructor(t=new Ar([new vt(0,.5),new vt(-.5,-.5),new vt(.5,-.5)]),e=12){super(),this.type="ShapeGeometry",this.parameters={shapes:t,curveSegments:e};let n=[],i=[],r=[],o=[],a=0,l=0;if(Array.isArray(t)===!1)c(t);else for(let h=0;h<t.length;h++)c(t[h]),this.addGroup(a,l,h),a+=l,l=0;this.setIndex(n),this.setAttribute("position",new hn(i,3)),this.setAttribute("normal",new hn(r,3)),this.setAttribute("uv",new hn(o,2));function c(h){let u=i.length/3,f=h.extractPoints(e),d=f.shape,g=f.holes;Fs.isClockWise(d)===!1&&(d=d.reverse());for(let m=0,p=g.length;m<p;m++){let S=g[m];Fs.isClockWise(S)===!0&&(g[m]=S.reverse())}let _=Fs.triangulateShape(d,g);for(let m=0,p=g.length;m<p;m++){let S=g[m];d=d.concat(S)}for(let m=0,p=d.length;m<p;m++){let S=d[m];i.push(S.x,S.y,0),r.push(0,0,1),o.push(S.x,S.y)}for(let m=0,p=_.length;m<p;m++){let S=_[m],y=S[0]+u,v=S[1]+u,E=S[2]+u;n.push(y,v,E),l+=3}}}copy(t){return super.copy(t),this.parameters=Object.assign({},t.parameters),this}toJSON(){let t=super.toJSON(),e=this.parameters.shapes;return Ow(e,t)}static fromJSON(t,e){let n=[];for(let i=0,r=t.shapes.length;i<r;i++){let o=e[t.shapes[i]];n.push(o)}return new s(n,t.curveSegments)}};function Ow(s,t){if(t.shapes=[],Array.isArray(s))for(let e=0,n=s.length;e<n;e++){let i=s[e];t.shapes.push(i.uuid)}else t.shapes.push(s.uuid);return t}var Hc=class extends je{static get type(){return"RawShaderMaterial"}constructor(t){super(t),this.isRawShaderMaterial=!0}},ls=class extends br{static get type(){return"MeshStandardMaterial"}constructor(t){super(),this.isMeshStandardMaterial=!0,this.defines={STANDARD:""},this.color=new se(16777215),this.roughness=1,this.metalness=0,this.map=null,this.lightMap=null,this.lightMapIntensity=1,this.aoMap=null,this.aoMapIntensity=1,this.emissive=new se(0),this.emissiveIntensity=1,this.emissiveMap=null,this.bumpMap=null,this.bumpScale=1,this.normalMap=null,this.normalMapType=z_,this.normalScale=new vt(1,1),this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.roughnessMap=null,this.metalnessMap=null,this.alphaMap=null,this.envMap=null,this.envMapRotation=new mi,this.envMapIntensity=1,this.wireframe=!1,this.wireframeLinewidth=1,this.wireframeLinecap="round",this.wireframeLinejoin="round",this.flatShading=!1,this.fog=!0,this.setValues(t)}copy(t){return super.copy(t),this.defines={STANDARD:""},this.color.copy(t.color),this.roughness=t.roughness,this.metalness=t.metalness,this.map=t.map,this.lightMap=t.lightMap,this.lightMapIntensity=t.lightMapIntensity,this.aoMap=t.aoMap,this.aoMapIntensity=t.aoMapIntensity,this.emissive.copy(t.emissive),this.emissiveMap=t.emissiveMap,this.emissiveIntensity=t.emissiveIntensity,this.bumpMap=t.bumpMap,this.bumpScale=t.bumpScale,this.normalMap=t.normalMap,this.normalMapType=t.normalMapType,this.normalScale.copy(t.normalScale),this.displacementMap=t.displacementMap,this.displacementScale=t.displacementScale,this.displacementBias=t.displacementBias,this.roughnessMap=t.roughnessMap,this.metalnessMap=t.metalnessMap,this.alphaMap=t.alphaMap,this.envMap=t.envMap,this.envMapRotation.copy(t.envMapRotation),this.envMapIntensity=t.envMapIntensity,this.wireframe=t.wireframe,this.wireframeLinewidth=t.wireframeLinewidth,this.wireframeLinecap=t.wireframeLinecap,this.wireframeLinejoin=t.wireframeLinejoin,this.flatShading=t.flatShading,this.fog=t.fog,this}};function mc(s,t,e){return!s||!e&&s.constructor===t?s:typeof t.BYTES_PER_ELEMENT=="number"?new t(s):Array.prototype.slice.call(s)}function Fw(s){return ArrayBuffer.isView(s)&&!(s instanceof DataView)}var Uo=class{constructor(t,e,n,i){this.parameterPositions=t,this._cachedIndex=0,this.resultBuffer=i!==void 0?i:new e.constructor(n),this.sampleValues=e,this.valueSize=n,this.settings=null,this.DefaultSettings_={}}evaluate(t){let e=this.parameterPositions,n=this._cachedIndex,i=e[n],r=e[n-1];n:{t:{let o;e:{i:if(!(t<i)){for(let a=n+2;;){if(i===void 0){if(t<r)break i;return n=e.length,this._cachedIndex=n,this.copySampleValue_(n-1)}if(n===a)break;if(r=i,i=e[++n],t<i)break t}o=e.length;break e}if(!(t>=r)){let a=e[1];t<a&&(n=2,r=a);for(let l=n-2;;){if(r===void 0)return this._cachedIndex=0,this.copySampleValue_(0);if(n===l)break;if(i=r,r=e[--n-1],t>=r)break t}o=n,n=0;break e}break n}for(;n<o;){let a=n+o>>>1;t<e[a]?o=a:n=a+1}if(i=e[n],r=e[n-1],r===void 0)return this._cachedIndex=0,this.copySampleValue_(0);if(i===void 0)return n=e.length,this._cachedIndex=n,this.copySampleValue_(n-1)}this._cachedIndex=n,this.intervalChanged_(n,r,i)}return this.interpolate_(n,r,t,i)}getSettings_(){return this.settings||this.DefaultSettings_}copySampleValue_(t){let e=this.resultBuffer,n=this.sampleValues,i=this.valueSize,r=t*i;for(let o=0;o!==i;++o)e[o]=n[r+o];return e}interpolate_(){throw new Error("call to abstract method")}intervalChanged_(){}},Md=class extends Uo{constructor(t,e,n,i){super(t,e,n,i),this._weightPrev=-0,this._offsetPrev=-0,this._weightNext=-0,this._offsetNext=-0,this.DefaultSettings_={endingStart:Sg,endingEnd:Sg}}intervalChanged_(t,e,n){let i=this.parameterPositions,r=t-2,o=t+1,a=i[r],l=i[o];if(a===void 0)switch(this.getSettings_().endingStart){case bg:r=t,a=2*e-n;break;case wg:r=i.length-2,a=e+i[r]-i[r+1];break;default:r=t,a=n}if(l===void 0)switch(this.getSettings_().endingEnd){case bg:o=t,l=2*n-e;break;case wg:o=1,l=n+i[1]-i[0];break;default:o=t-1,l=e}let c=(n-e)*.5,h=this.valueSize;this._weightPrev=c/(e-a),this._weightNext=c/(l-n),this._offsetPrev=r*h,this._offsetNext=o*h}interpolate_(t,e,n,i){let r=this.resultBuffer,o=this.sampleValues,a=this.valueSize,l=t*a,c=l-a,h=this._offsetPrev,u=this._offsetNext,f=this._weightPrev,d=this._weightNext,g=(n-e)/(i-e),_=g*g,m=_*g,p=-f*m+2*f*_-f*g,S=(1+f)*m+(-1.5-2*f)*_+(-.5+f)*g+1,y=(-1-d)*m+(1.5+d)*_+.5*g,v=d*m-d*_;for(let E=0;E!==a;++E)r[E]=p*o[h+E]+S*o[c+E]+y*o[l+E]+v*o[u+E];return r}},Sd=class extends Uo{constructor(t,e,n,i){super(t,e,n,i)}interpolate_(t,e,n,i){let r=this.resultBuffer,o=this.sampleValues,a=this.valueSize,l=t*a,c=l-a,h=(n-e)/(i-e),u=1-h;for(let f=0;f!==a;++f)r[f]=o[c+f]*u+o[l+f]*h;return r}},bd=class extends Uo{constructor(t,e,n,i){super(t,e,n,i)}interpolate_(t){return this.copySampleValue_(t-1)}},Ai=class{constructor(t,e,n,i){if(t===void 0)throw new Error("THREE.KeyframeTrack: track name is undefined");if(e===void 0||e.length===0)throw new Error("THREE.KeyframeTrack: no keyframes in track named "+t);this.name=t,this.times=mc(e,this.TimeBufferType),this.values=mc(n,this.ValueBufferType),this.setInterpolation(i||this.DefaultInterpolation)}static toJSON(t){let e=t.constructor,n;if(e.toJSON!==this.toJSON)n=e.toJSON(t);else{n={name:t.name,times:mc(t.times,Array),values:mc(t.values,Array)};let i=t.getInterpolation();i!==t.DefaultInterpolation&&(n.interpolation=i)}return n.type=t.ValueTypeName,n}InterpolantFactoryMethodDiscrete(t){return new bd(this.times,this.values,this.getValueSize(),t)}InterpolantFactoryMethodLinear(t){return new Sd(this.times,this.values,this.getValueSize(),t)}InterpolantFactoryMethodSmooth(t){return new Md(this.times,this.values,this.getValueSize(),t)}setInterpolation(t){let e;switch(t){case Sc:e=this.InterpolantFactoryMethodDiscrete;break;case Yf:e=this.InterpolantFactoryMethodLinear;break;case Eu:e=this.InterpolantFactoryMethodSmooth;break}if(e===void 0){let n="unsupported interpolation for "+this.ValueTypeName+" keyframe track named "+this.name;if(this.createInterpolant===void 0)if(t!==this.DefaultInterpolation)this.setInterpolation(this.DefaultInterpolation);else throw new Error(n);return console.warn("THREE.KeyframeTrack:",n),this}return this.createInterpolant=e,this}getInterpolation(){switch(this.createInterpolant){case this.InterpolantFactoryMethodDiscrete:return Sc;case this.InterpolantFactoryMethodLinear:return Yf;case this.InterpolantFactoryMethodSmooth:return Eu}}getValueSize(){return this.values.length/this.times.length}shift(t){if(t!==0){let e=this.times;for(let n=0,i=e.length;n!==i;++n)e[n]+=t}return this}scale(t){if(t!==1){let e=this.times;for(let n=0,i=e.length;n!==i;++n)e[n]*=t}return this}trim(t,e){let n=this.times,i=n.length,r=0,o=i-1;for(;r!==i&&n[r]<t;)++r;for(;o!==-1&&n[o]>e;)--o;if(++o,r!==0||o!==i){r>=o&&(o=Math.max(o,1),r=o-1);let a=this.getValueSize();this.times=n.slice(r,o),this.values=this.values.slice(r*a,o*a)}return this}validate(){let t=!0,e=this.getValueSize();e-Math.floor(e)!==0&&(console.error("THREE.KeyframeTrack: Invalid value size in track.",this),t=!1);let n=this.times,i=this.values,r=n.length;r===0&&(console.error("THREE.KeyframeTrack: Track is empty.",this),t=!1);let o=null;for(let a=0;a!==r;a++){let l=n[a];if(typeof l=="number"&&isNaN(l)){console.error("THREE.KeyframeTrack: Time is not a valid number.",this,a,l),t=!1;break}if(o!==null&&o>l){console.error("THREE.KeyframeTrack: Out of order keys.",this,a,l,o),t=!1;break}o=l}if(i!==void 0&&Fw(i))for(let a=0,l=i.length;a!==l;++a){let c=i[a];if(isNaN(c)){console.error("THREE.KeyframeTrack: Value is not a valid number.",this,a,c),t=!1;break}}return t}optimize(){let t=this.times.slice(),e=this.values.slice(),n=this.getValueSize(),i=this.getInterpolation()===Eu,r=t.length-1,o=1;for(let a=1;a<r;++a){let l=!1,c=t[a],h=t[a+1];if(c!==h&&(a!==1||c!==t[0]))if(i)l=!0;else{let u=a*n,f=u-n,d=u+n;for(let g=0;g!==n;++g){let _=e[u+g];if(_!==e[f+g]||_!==e[d+g]){l=!0;break}}}if(l){if(a!==o){t[o]=t[a];let u=a*n,f=o*n;for(let d=0;d!==n;++d)e[f+d]=e[u+d]}++o}}if(r>0){t[o]=t[r];for(let a=r*n,l=o*n,c=0;c!==n;++c)e[l+c]=e[a+c];++o}return o!==t.length?(this.times=t.slice(0,o),this.values=e.slice(0,o*n)):(this.times=t,this.values=e),this}clone(){let t=this.times.slice(),e=this.values.slice(),n=this.constructor,i=new n(this.name,t,e);return i.createInterpolant=this.createInterpolant,i}};Ai.prototype.TimeBufferType=Float32Array;Ai.prototype.ValueBufferType=Float32Array;Ai.prototype.DefaultInterpolation=Yf;var Rr=class extends Ai{constructor(t,e,n){super(t,e,n)}};Rr.prototype.ValueTypeName="bool";Rr.prototype.ValueBufferType=Array;Rr.prototype.DefaultInterpolation=Sc;Rr.prototype.InterpolantFactoryMethodLinear=void 0;Rr.prototype.InterpolantFactoryMethodSmooth=void 0;var wd=class extends Ai{};wd.prototype.ValueTypeName="color";var Td=class extends Ai{};Td.prototype.ValueTypeName="number";var Ed=class extends Uo{constructor(t,e,n,i){super(t,e,n,i)}interpolate_(t,e,n,i){let r=this.resultBuffer,o=this.sampleValues,a=this.valueSize,l=(n-e)/(i-e),c=t*a;for(let h=c+a;c!==h;c+=4)wi.slerpFlat(r,0,o,c-a,o,c,l);return r}},Gc=class extends Ai{InterpolantFactoryMethodLinear(t){return new Ed(this.times,this.values,this.getValueSize(),t)}};Gc.prototype.ValueTypeName="quaternion";Gc.prototype.InterpolantFactoryMethodSmooth=void 0;var Pr=class extends Ai{constructor(t,e,n){super(t,e,n)}};Pr.prototype.ValueTypeName="string";Pr.prototype.ValueBufferType=Array;Pr.prototype.DefaultInterpolation=Sc;Pr.prototype.InterpolantFactoryMethodLinear=void 0;Pr.prototype.InterpolantFactoryMethodSmooth=void 0;var Ad=class extends Ai{};Ad.prototype.ValueTypeName="vector";var Cd=class{constructor(t,e,n){let i=this,r=!1,o=0,a=0,l,c=[];this.onStart=void 0,this.onLoad=t,this.onProgress=e,this.onError=n,this.itemStart=function(h){a++,r===!1&&i.onStart!==void 0&&i.onStart(h,o,a),r=!0},this.itemEnd=function(h){o++,i.onProgress!==void 0&&i.onProgress(h,o,a),o===a&&(r=!1,i.onLoad!==void 0&&i.onLoad())},this.itemError=function(h){i.onError!==void 0&&i.onError(h)},this.resolveURL=function(h){return l?l(h):h},this.setURLModifier=function(h){return l=h,this},this.addHandler=function(h,u){return c.push(h,u),this},this.removeHandler=function(h){let u=c.indexOf(h);return u!==-1&&c.splice(u,2),this},this.getHandler=function(h){for(let u=0,f=c.length;u<f;u+=2){let d=c[u],g=c[u+1];if(d.global&&(d.lastIndex=0),d.test(h))return g}return null}}},Bw=new Cd,Rd=class{constructor(t){this.manager=t!==void 0?t:Bw,this.crossOrigin="anonymous",this.withCredentials=!1,this.path="",this.resourcePath="",this.requestHeader={}}load(){}loadAsync(t,e){let n=this;return new Promise(function(i,r){n.load(t,i,e,r)})}parse(){}setCrossOrigin(t){return this.crossOrigin=t,this}setWithCredentials(t){return this.withCredentials=t,this}setPath(t){return this.path=t,this}setResourcePath(t){return this.resourcePath=t,this}setRequestHeader(t){return this.requestHeader=t,this}};Rd.DEFAULT_MATERIAL_NAME="__DEFAULT";var Wc=class extends Hn{constructor(t,e=1){super(),this.isLight=!0,this.type="Light",this.color=new se(t),this.intensity=e}dispose(){}copy(t,e){return super.copy(t,e),this.color.copy(t.color),this.intensity=t.intensity,this}toJSON(t){let e=super.toJSON(t);return e.object.color=this.color.getHex(),e.object.intensity=this.intensity,this.groundColor!==void 0&&(e.object.groundColor=this.groundColor.getHex()),this.distance!==void 0&&(e.object.distance=this.distance),this.angle!==void 0&&(e.object.angle=this.angle),this.decay!==void 0&&(e.object.decay=this.decay),this.penumbra!==void 0&&(e.object.penumbra=this.penumbra),this.shadow!==void 0&&(e.object.shadow=this.shadow.toJSON()),this.target!==void 0&&(e.object.target=this.target.uuid),e}};var rf=new Ce,w_=new B,T_=new B,Xc=class{constructor(t){this.camera=t,this.intensity=1,this.bias=0,this.normalBias=0,this.radius=1,this.blurSamples=8,this.mapSize=new vt(512,512),this.map=null,this.mapPass=null,this.matrix=new Ce,this.autoUpdate=!0,this.needsUpdate=!1,this._frustum=new Va,this._frameExtents=new vt(1,1),this._viewportCount=1,this._viewports=[new Ae(0,0,1,1)]}getViewportCount(){return this._viewportCount}getFrustum(){return this._frustum}updateMatrices(t){let e=this.camera,n=this.matrix;w_.setFromMatrixPosition(t.matrixWorld),e.position.copy(w_),T_.setFromMatrixPosition(t.target.matrixWorld),e.lookAt(T_),e.updateMatrixWorld(),rf.multiplyMatrices(e.projectionMatrix,e.matrixWorldInverse),this._frustum.setFromProjectionMatrix(rf),n.set(.5,0,0,.5,0,.5,0,.5,0,0,.5,.5,0,0,0,1),n.multiply(rf)}getViewport(t){return this._viewports[t]}getFrameExtents(){return this._frameExtents}dispose(){this.map&&this.map.dispose(),this.mapPass&&this.mapPass.dispose()}copy(t){return this.camera=t.camera.clone(),this.intensity=t.intensity,this.bias=t.bias,this.radius=t.radius,this.mapSize.copy(t.mapSize),this}clone(){return new this.constructor().copy(this)}toJSON(){let t={};return this.intensity!==1&&(t.intensity=this.intensity),this.bias!==0&&(t.bias=this.bias),this.normalBias!==0&&(t.normalBias=this.normalBias),this.radius!==1&&(t.radius=this.radius),(this.mapSize.x!==512||this.mapSize.y!==512)&&(t.mapSize=this.mapSize.toArray()),t.camera=this.camera.toJSON(!1).object,delete t.camera.matrix,t}};var E_=new Ce,Ua=new B,of=new B,Pd=class extends Xc{constructor(){super(new bn(90,1,.5,500)),this.isPointLightShadow=!0,this._frameExtents=new vt(4,2),this._viewportCount=6,this._viewports=[new Ae(2,1,1,1),new Ae(0,1,1,1),new Ae(3,1,1,1),new Ae(1,1,1,1),new Ae(3,0,1,1),new Ae(1,0,1,1)],this._cubeDirections=[new B(1,0,0),new B(-1,0,0),new B(0,0,1),new B(0,0,-1),new B(0,1,0),new B(0,-1,0)],this._cubeUps=[new B(0,1,0),new B(0,1,0),new B(0,1,0),new B(0,1,0),new B(0,0,1),new B(0,0,-1)]}updateMatrices(t,e=0){let n=this.camera,i=this.matrix,r=t.distance||n.far;r!==n.far&&(n.far=r,n.updateProjectionMatrix()),Ua.setFromMatrixPosition(t.matrixWorld),n.position.copy(Ua),of.copy(n.position),of.add(this._cubeDirections[e]),n.up.copy(this._cubeUps[e]),n.lookAt(of),n.updateMatrixWorld(),i.makeTranslation(-Ua.x,-Ua.y,-Ua.z),E_.multiplyMatrices(n.projectionMatrix,n.matrixWorldInverse),this._frustum.setFromProjectionMatrix(E_)}},No=class extends Wc{constructor(t,e,n=0,i=2){super(t,e),this.isPointLight=!0,this.type="PointLight",this.distance=n,this.decay=i,this.shadow=new Pd}get power(){return this.intensity*4*Math.PI}set power(t){this.intensity=t/(4*Math.PI)}dispose(){this.shadow.dispose()}copy(t,e){return super.copy(t,e),this.distance=t.distance,this.decay=t.decay,this.shadow=t.shadow.clone(),this}},Id=class extends Xc{constructor(){super(new Po(-5,5,5,-5,.5,500)),this.isDirectionalLightShadow=!0}},Yc=class extends Wc{constructor(t,e){super(t,e),this.isDirectionalLight=!0,this.type="DirectionalLight",this.position.copy(Hn.DEFAULT_UP),this.updateMatrix(),this.target=new Hn,this.shadow=new Id}dispose(){this.shadow.dispose()}copy(t){return super.copy(t),this.target=t.target.clone(),this.shadow=t.shadow.clone(),this}};var qc=class{constructor(t=!0){this.autoStart=t,this.startTime=0,this.oldTime=0,this.elapsedTime=0,this.running=!1}start(){this.startTime=A_(),this.oldTime=this.startTime,this.elapsedTime=0,this.running=!0}stop(){this.getElapsedTime(),this.running=!1,this.autoStart=!1}getElapsedTime(){return this.getDelta(),this.elapsedTime}getDelta(){let t=0;if(this.autoStart&&!this.running)return this.start(),0;if(this.running){let e=A_();t=(e-this.oldTime)/1e3,this.oldTime=e,this.elapsedTime+=t}return t}};function A_(){return performance.now()}var Zd="\\[\\]\\.:\\/",kw=new RegExp("["+Zd+"]","g"),$d="[^"+Zd+"]",zw="[^"+Zd.replace("\\.","")+"]",Vw=/((?:WC+[\/:])*)/.source.replace("WC",$d),Hw=/(WCOD+)?/.source.replace("WCOD",zw),Gw=/(?:\.(WC+)(?:\[(.+)\])?)?/.source.replace("WC",$d),Ww=/\.(WC+)(?:\[(.+)\])?/.source.replace("WC",$d),Xw=new RegExp("^"+Vw+Hw+Gw+Ww+"$"),Yw=["material","materials","bones","map"],Ld=class{constructor(t,e,n){let i=n||Oe.parseTrackName(e);this._targetGroup=t,this._bindings=t.subscribe_(e,i)}getValue(t,e){this.bind();let n=this._targetGroup.nCachedObjects_,i=this._bindings[n];i!==void 0&&i.getValue(t,e)}setValue(t,e){let n=this._bindings;for(let i=this._targetGroup.nCachedObjects_,r=n.length;i!==r;++i)n[i].setValue(t,e)}bind(){let t=this._bindings;for(let e=this._targetGroup.nCachedObjects_,n=t.length;e!==n;++e)t[e].bind()}unbind(){let t=this._bindings;for(let e=this._targetGroup.nCachedObjects_,n=t.length;e!==n;++e)t[e].unbind()}},Oe=class s{constructor(t,e,n){this.path=e,this.parsedPath=n||s.parseTrackName(e),this.node=s.findNode(t,this.parsedPath.nodeName),this.rootNode=t,this.getValue=this._getValue_unbound,this.setValue=this._setValue_unbound}static create(t,e,n){return t&&t.isAnimationObjectGroup?new s.Composite(t,e,n):new s(t,e,n)}static sanitizeNodeName(t){return t.replace(/\s/g,"_").replace(kw,"")}static parseTrackName(t){let e=Xw.exec(t);if(e===null)throw new Error("PropertyBinding: Cannot parse trackName: "+t);let n={nodeName:e[2],objectName:e[3],objectIndex:e[4],propertyName:e[5],propertyIndex:e[6]},i=n.nodeName&&n.nodeName.lastIndexOf(".");if(i!==void 0&&i!==-1){let r=n.nodeName.substring(i+1);Yw.indexOf(r)!==-1&&(n.nodeName=n.nodeName.substring(0,i),n.objectName=r)}if(n.propertyName===null||n.propertyName.length===0)throw new Error("PropertyBinding: can not parse propertyName from trackName: "+t);return n}static findNode(t,e){if(e===void 0||e===""||e==="."||e===-1||e===t.name||e===t.uuid)return t;if(t.skeleton){let n=t.skeleton.getBoneByName(e);if(n!==void 0)return n}if(t.children){let n=function(r){for(let o=0;o<r.length;o++){let a=r[o];if(a.name===e||a.uuid===e)return a;let l=n(a.children);if(l)return l}return null},i=n(t.children);if(i)return i}return null}_getValue_unavailable(){}_setValue_unavailable(){}_getValue_direct(t,e){t[e]=this.targetObject[this.propertyName]}_getValue_array(t,e){let n=this.resolvedProperty;for(let i=0,r=n.length;i!==r;++i)t[e++]=n[i]}_getValue_arrayElement(t,e){t[e]=this.resolvedProperty[this.propertyIndex]}_getValue_toArray(t,e){this.resolvedProperty.toArray(t,e)}_setValue_direct(t,e){this.targetObject[this.propertyName]=t[e]}_setValue_direct_setNeedsUpdate(t,e){this.targetObject[this.propertyName]=t[e],this.targetObject.needsUpdate=!0}_setValue_direct_setMatrixWorldNeedsUpdate(t,e){this.targetObject[this.propertyName]=t[e],this.targetObject.matrixWorldNeedsUpdate=!0}_setValue_array(t,e){let n=this.resolvedProperty;for(let i=0,r=n.length;i!==r;++i)n[i]=t[e++]}_setValue_array_setNeedsUpdate(t,e){let n=this.resolvedProperty;for(let i=0,r=n.length;i!==r;++i)n[i]=t[e++];this.targetObject.needsUpdate=!0}_setValue_array_setMatrixWorldNeedsUpdate(t,e){let n=this.resolvedProperty;for(let i=0,r=n.length;i!==r;++i)n[i]=t[e++];this.targetObject.matrixWorldNeedsUpdate=!0}_setValue_arrayElement(t,e){this.resolvedProperty[this.propertyIndex]=t[e]}_setValue_arrayElement_setNeedsUpdate(t,e){this.resolvedProperty[this.propertyIndex]=t[e],this.targetObject.needsUpdate=!0}_setValue_arrayElement_setMatrixWorldNeedsUpdate(t,e){this.resolvedProperty[this.propertyIndex]=t[e],this.targetObject.matrixWorldNeedsUpdate=!0}_setValue_fromArray(t,e){this.resolvedProperty.fromArray(t,e)}_setValue_fromArray_setNeedsUpdate(t,e){this.resolvedProperty.fromArray(t,e),this.targetObject.needsUpdate=!0}_setValue_fromArray_setMatrixWorldNeedsUpdate(t,e){this.resolvedProperty.fromArray(t,e),this.targetObject.matrixWorldNeedsUpdate=!0}_getValue_unbound(t,e){this.bind(),this.getValue(t,e)}_setValue_unbound(t,e){this.bind(),this.setValue(t,e)}bind(){let t=this.node,e=this.parsedPath,n=e.objectName,i=e.propertyName,r=e.propertyIndex;if(t||(t=s.findNode(this.rootNode,e.nodeName),this.node=t),this.getValue=this._getValue_unavailable,this.setValue=this._setValue_unavailable,!t){console.warn("THREE.PropertyBinding: No target node found for track: "+this.path+".");return}if(n){let c=e.objectIndex;switch(n){case"materials":if(!t.material){console.error("THREE.PropertyBinding: Can not bind to material as node does not have a material.",this);return}if(!t.material.materials){console.error("THREE.PropertyBinding: Can not bind to material.materials as node.material does not have a materials array.",this);return}t=t.material.materials;break;case"bones":if(!t.skeleton){console.error("THREE.PropertyBinding: Can not bind to bones as node does not have a skeleton.",this);return}t=t.skeleton.bones;for(let h=0;h<t.length;h++)if(t[h].name===c){c=h;break}break;case"map":if("map"in t){t=t.map;break}if(!t.material){console.error("THREE.PropertyBinding: Can not bind to material as node does not have a material.",this);return}if(!t.material.map){console.error("THREE.PropertyBinding: Can not bind to material.map as node.material does not have a map.",this);return}t=t.material.map;break;default:if(t[n]===void 0){console.error("THREE.PropertyBinding: Can not bind to objectName of node undefined.",this);return}t=t[n]}if(c!==void 0){if(t[c]===void 0){console.error("THREE.PropertyBinding: Trying to bind to objectIndex of objectName, but is undefined.",this,t);return}t=t[c]}}let o=t[i];if(o===void 0){let c=e.nodeName;console.error("THREE.PropertyBinding: Trying to update property for track: "+c+"."+i+" but it wasn't found.",t);return}let a=this.Versioning.None;this.targetObject=t,t.needsUpdate!==void 0?a=this.Versioning.NeedsUpdate:t.matrixWorldNeedsUpdate!==void 0&&(a=this.Versioning.MatrixWorldNeedsUpdate);let l=this.BindingType.Direct;if(r!==void 0){if(i==="morphTargetInfluences"){if(!t.geometry){console.error("THREE.PropertyBinding: Can not bind to morphTargetInfluences because node does not have a geometry.",this);return}if(!t.geometry.morphAttributes){console.error("THREE.PropertyBinding: Can not bind to morphTargetInfluences because node does not have a geometry.morphAttributes.",this);return}t.morphTargetDictionary[r]!==void 0&&(r=t.morphTargetDictionary[r])}l=this.BindingType.ArrayElement,this.resolvedProperty=o,this.propertyIndex=r}else o.fromArray!==void 0&&o.toArray!==void 0?(l=this.BindingType.HasFromToArray,this.resolvedProperty=o):Array.isArray(o)?(l=this.BindingType.EntireArray,this.resolvedProperty=o):this.propertyName=i;this.getValue=this.GetterByBindingType[l],this.setValue=this.SetterByBindingTypeAndVersioning[l][a]}unbind(){this.node=null,this.getValue=this._getValue_unbound,this.setValue=this._setValue_unbound}};Oe.Composite=Ld;Oe.prototype.BindingType={Direct:0,EntireArray:1,ArrayElement:2,HasFromToArray:3};Oe.prototype.Versioning={None:0,NeedsUpdate:1,MatrixWorldNeedsUpdate:2};Oe.prototype.GetterByBindingType=[Oe.prototype._getValue_direct,Oe.prototype._getValue_array,Oe.prototype._getValue_arrayElement,Oe.prototype._getValue_toArray];Oe.prototype.SetterByBindingTypeAndVersioning=[[Oe.prototype._setValue_direct,Oe.prototype._setValue_direct_setNeedsUpdate,Oe.prototype._setValue_direct_setMatrixWorldNeedsUpdate],[Oe.prototype._setValue_array,Oe.prototype._setValue_array_setNeedsUpdate,Oe.prototype._setValue_array_setMatrixWorldNeedsUpdate],[Oe.prototype._setValue_arrayElement,Oe.prototype._setValue_arrayElement_setNeedsUpdate,Oe.prototype._setValue_arrayElement_setMatrixWorldNeedsUpdate],[Oe.prototype._setValue_fromArray,Oe.prototype._setValue_fromArray_setNeedsUpdate,Oe.prototype._setValue_fromArray_setMatrixWorldNeedsUpdate]];var bT=new Float32Array(1);typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("register",{detail:{revision:"170"}}));typeof window<"u"&&(window.__THREE__?console.warn("WARNING: Multiple instances of Three.js being imported."):window.__THREE__="170");var Qc=class extends Lo{constructor(){super();let t=new wr;t.deleteAttribute("uv");let e=new ls({side:wn}),n=new ls,i=new No(16777215,900,28,2);i.position.set(.418,16.199,.3),this.add(i);let r=new ve(t,e);r.position.set(-.757,13.219,.717),r.scale.set(31.713,28.305,28.591),this.add(r);let o=new ve(t,n);o.position.set(-10.906,2.009,1.846),o.rotation.set(0,-.195,0),o.scale.set(2.328,7.905,4.651),this.add(o);let a=new ve(t,n);a.position.set(-5.607,-.754,-.758),a.rotation.set(0,.994,0),a.scale.set(1.97,1.534,3.955),this.add(a);let l=new ve(t,n);l.position.set(6.167,.857,7.803),l.rotation.set(0,.561,0),l.scale.set(3.927,6.285,3.687),this.add(l);let c=new ve(t,n);c.position.set(-2.017,.018,6.124),c.rotation.set(0,.333,0),c.scale.set(2.002,4.566,2.064),this.add(c);let h=new ve(t,n);h.position.set(2.291,-.756,-2.621),h.rotation.set(0,-.286,0),h.scale.set(1.546,1.552,1.496),this.add(h);let u=new ve(t,n);u.position.set(-2.193,-.369,-5.547),u.rotation.set(0,.516,0),u.scale.set(3.875,3.487,2.986),this.add(u);let f=new ve(t,ko(50));f.position.set(-16.116,14.37,8.208),f.scale.set(.1,2.428,2.739),this.add(f);let d=new ve(t,ko(50));d.position.set(-16.109,18.021,-8.207),d.scale.set(.1,2.425,2.751),this.add(d);let g=new ve(t,ko(17));g.position.set(14.904,12.198,-1.832),g.scale.set(.15,4.265,6.331),this.add(g);let _=new ve(t,ko(43));_.position.set(-.462,8.89,14.52),_.scale.set(4.38,5.441,.088),this.add(_);let m=new ve(t,ko(20));m.position.set(3.235,11.486,-12.541),m.scale.set(2.5,2,.1),this.add(m);let p=new ve(t,ko(100));p.position.set(0,20,0),p.scale.set(1,.1,1),this.add(p)}dispose(){let t=new Set;this.traverse(e=>{e.isMesh&&(t.add(e.geometry),t.add(e.material))});for(let e of t)e.dispose()}};function ko(s){let t=new Ti;return t.color.setScalar(s),t}var jc={name:"CopyShader",uniforms:{tDiffuse:{value:null},opacity:{value:1}},vertexShader:`

		varying vec2 vUv;

		void main() {

			vUv = uv;
			gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );

		}`,fragmentShader:`

		uniform float opacity;

		uniform sampler2D tDiffuse;

		varying vec2 vUv;

		void main() {

			vec4 texel = texture2D( tDiffuse, vUv );
			gl_FragColor = opacity * texel;


		}`};var ni=class{constructor(){this.isPass=!0,this.enabled=!0,this.needsSwap=!0,this.clear=!1,this.renderToScreen=!1}setSize(){}render(){console.error("THREE.Pass: .render() must be implemented in derived pass.")}dispose(){}},Zw=new Po(-1,1,1,-1,0,1),Jd=class extends Ei{constructor(){super(),this.setAttribute("position",new hn([-1,3,0,-1,-1,0,3,-1,0],3)),this.setAttribute("uv",new hn([0,2,0,0,2,0],2))}},$w=new Jd,Vs=class{constructor(t){this._mesh=new ve($w,t)}dispose(){this._mesh.geometry.dispose()}render(t){t.render(this._mesh,Zw)}get material(){return this._mesh.material}set material(t){this._mesh.material=t}};var zo=class extends ni{constructor(t,e){super(),this.textureID=e!==void 0?e:"tDiffuse",t instanceof je?(this.uniforms=t.uniforms,this.material=t):t&&(this.uniforms=zs.clone(t.uniforms),this.material=new je({name:t.name!==void 0?t.name:"unspecified",defines:Object.assign({},t.defines),uniforms:this.uniforms,vertexShader:t.vertexShader,fragmentShader:t.fragmentShader})),this.fsQuad=new Vs(this.material)}render(t,e,n){this.uniforms[this.textureID]&&(this.uniforms[this.textureID].value=n.texture),this.fsQuad.material=this.material,this.renderToScreen?(t.setRenderTarget(null),this.fsQuad.render(t)):(t.setRenderTarget(e),this.clear&&t.clear(t.autoClearColor,t.autoClearDepth,t.autoClearStencil),this.fsQuad.render(t))}dispose(){this.material.dispose(),this.fsQuad.dispose()}};var Za=class extends ni{constructor(t,e){super(),this.scene=t,this.camera=e,this.clear=!0,this.needsSwap=!1,this.inverse=!1}render(t,e,n){let i=t.getContext(),r=t.state;r.buffers.color.setMask(!1),r.buffers.depth.setMask(!1),r.buffers.color.setLocked(!0),r.buffers.depth.setLocked(!0);let o,a;this.inverse?(o=0,a=1):(o=1,a=0),r.buffers.stencil.setTest(!0),r.buffers.stencil.setOp(i.REPLACE,i.REPLACE,i.REPLACE),r.buffers.stencil.setFunc(i.ALWAYS,o,4294967295),r.buffers.stencil.setClear(a),r.buffers.stencil.setLocked(!0),t.setRenderTarget(n),this.clear&&t.clear(),t.render(this.scene,this.camera),t.setRenderTarget(e),this.clear&&t.clear(),t.render(this.scene,this.camera),r.buffers.color.setLocked(!1),r.buffers.depth.setLocked(!1),r.buffers.color.setMask(!0),r.buffers.depth.setMask(!0),r.buffers.stencil.setLocked(!1),r.buffers.stencil.setFunc(i.EQUAL,1,4294967295),r.buffers.stencil.setOp(i.KEEP,i.KEEP,i.KEEP),r.buffers.stencil.setLocked(!0)}},th=class extends ni{constructor(){super(),this.needsSwap=!1}render(t){t.state.buffers.stencil.setLocked(!1),t.state.buffers.stencil.setTest(!1)}};var eh=class{constructor(t,e){if(this.renderer=t,this._pixelRatio=t.getPixelRatio(),e===void 0){let n=t.getSize(new vt);this._width=n.width,this._height=n.height,e=new un(this._width*this._pixelRatio,this._height*this._pixelRatio,{type:ei}),e.texture.name="EffectComposer.rt1"}else this._width=e.width,this._height=e.height;this.renderTarget1=e,this.renderTarget2=e.clone(),this.renderTarget2.texture.name="EffectComposer.rt2",this.writeBuffer=this.renderTarget1,this.readBuffer=this.renderTarget2,this.renderToScreen=!0,this.passes=[],this.copyPass=new zo(jc),this.copyPass.material.blending=ki,this.clock=new qc}swapBuffers(){let t=this.readBuffer;this.readBuffer=this.writeBuffer,this.writeBuffer=t}addPass(t){this.passes.push(t),t.setSize(this._width*this._pixelRatio,this._height*this._pixelRatio)}insertPass(t,e){this.passes.splice(e,0,t),t.setSize(this._width*this._pixelRatio,this._height*this._pixelRatio)}removePass(t){let e=this.passes.indexOf(t);e!==-1&&this.passes.splice(e,1)}isLastEnabledPass(t){for(let e=t+1;e<this.passes.length;e++)if(this.passes[e].enabled)return!1;return!0}render(t){t===void 0&&(t=this.clock.getDelta());let e=this.renderer.getRenderTarget(),n=!1;for(let i=0,r=this.passes.length;i<r;i++){let o=this.passes[i];if(o.enabled!==!1){if(o.renderToScreen=this.renderToScreen&&this.isLastEnabledPass(i),o.render(this.renderer,this.writeBuffer,this.readBuffer,t,n),o.needsSwap){if(n){let a=this.renderer.getContext(),l=this.renderer.state.buffers.stencil;l.setFunc(a.NOTEQUAL,1,4294967295),this.copyPass.render(this.renderer,this.writeBuffer,this.readBuffer,t),l.setFunc(a.EQUAL,1,4294967295)}this.swapBuffers()}Za!==void 0&&(o instanceof Za?n=!0:o instanceof th&&(n=!1))}}this.renderer.setRenderTarget(e)}reset(t){if(t===void 0){let e=this.renderer.getSize(new vt);this._pixelRatio=this.renderer.getPixelRatio(),this._width=e.width,this._height=e.height,t=this.renderTarget1.clone(),t.setSize(this._width*this._pixelRatio,this._height*this._pixelRatio)}this.renderTarget1.dispose(),this.renderTarget2.dispose(),this.renderTarget1=t,this.renderTarget2=t.clone(),this.writeBuffer=this.renderTarget1,this.readBuffer=this.renderTarget2}setSize(t,e){this._width=t,this._height=e;let n=this._width*this._pixelRatio,i=this._height*this._pixelRatio;this.renderTarget1.setSize(n,i),this.renderTarget2.setSize(n,i);for(let r=0;r<this.passes.length;r++)this.passes[r].setSize(n,i)}setPixelRatio(t){this._pixelRatio=t,this.setSize(this._width,this._height)}dispose(){this.renderTarget1.dispose(),this.renderTarget2.dispose(),this.copyPass.dispose()}};var nh=class extends ni{constructor(t,e,n=null,i=null,r=null){super(),this.scene=t,this.camera=e,this.overrideMaterial=n,this.clearColor=i,this.clearAlpha=r,this.clear=!0,this.clearDepth=!1,this.needsSwap=!1,this._oldClearColor=new se}render(t,e,n){let i=t.autoClear;t.autoClear=!1;let r,o;this.overrideMaterial!==null&&(o=this.scene.overrideMaterial,this.scene.overrideMaterial=this.overrideMaterial),this.clearColor!==null&&(t.getClearColor(this._oldClearColor),t.setClearColor(this.clearColor,t.getClearAlpha())),this.clearAlpha!==null&&(r=t.getClearAlpha(),t.setClearAlpha(this.clearAlpha)),this.clearDepth==!0&&t.clearDepth(),t.setRenderTarget(this.renderToScreen?null:n),this.clear===!0&&t.clear(t.autoClearColor,t.autoClearDepth,t.autoClearStencil),t.render(this.scene,this.camera),this.clearColor!==null&&t.setClearColor(this._oldClearColor),this.clearAlpha!==null&&t.setClearAlpha(r),this.overrideMaterial!==null&&(this.scene.overrideMaterial=o),t.autoClear=i}};var j_={name:"LuminosityHighPassShader",shaderID:"luminosityHighPass",uniforms:{tDiffuse:{value:null},luminosityThreshold:{value:1},smoothWidth:{value:1},defaultColor:{value:new se(0)},defaultOpacity:{value:0}},vertexShader:`

		varying vec2 vUv;

		void main() {

			vUv = uv;

			gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );

		}`,fragmentShader:`

		uniform sampler2D tDiffuse;
		uniform vec3 defaultColor;
		uniform float defaultOpacity;
		uniform float luminosityThreshold;
		uniform float smoothWidth;

		varying vec2 vUv;

		void main() {

			vec4 texel = texture2D( tDiffuse, vUv );

			float v = luminance( texel.xyz );

			vec4 outputColor = vec4( defaultColor.rgb, defaultOpacity );

			float alpha = smoothstep( luminosityThreshold, luminosityThreshold + smoothWidth, v );

			gl_FragColor = mix( outputColor, texel, alpha );

		}`};var Vo=class s extends ni{constructor(t,e,n,i){super(),this.strength=e!==void 0?e:1,this.radius=n,this.threshold=i,this.resolution=t!==void 0?new vt(t.x,t.y):new vt(256,256),this.clearColor=new se(0,0,0),this.renderTargetsHorizontal=[],this.renderTargetsVertical=[],this.nMips=5;let r=Math.round(this.resolution.x/2),o=Math.round(this.resolution.y/2);this.renderTargetBright=new un(r,o,{type:ei}),this.renderTargetBright.texture.name="UnrealBloomPass.bright",this.renderTargetBright.texture.generateMipmaps=!1;for(let u=0;u<this.nMips;u++){let f=new un(r,o,{type:ei});f.texture.name="UnrealBloomPass.h"+u,f.texture.generateMipmaps=!1,this.renderTargetsHorizontal.push(f);let d=new un(r,o,{type:ei});d.texture.name="UnrealBloomPass.v"+u,d.texture.generateMipmaps=!1,this.renderTargetsVertical.push(d),r=Math.round(r/2),o=Math.round(o/2)}let a=j_;this.highPassUniforms=zs.clone(a.uniforms),this.highPassUniforms.luminosityThreshold.value=i,this.highPassUniforms.smoothWidth.value=.01,this.materialHighPassFilter=new je({uniforms:this.highPassUniforms,vertexShader:a.vertexShader,fragmentShader:a.fragmentShader}),this.separableBlurMaterials=[];let l=[3,5,7,9,11];r=Math.round(this.resolution.x/2),o=Math.round(this.resolution.y/2);for(let u=0;u<this.nMips;u++)this.separableBlurMaterials.push(this.getSeperableBlurMaterial(l[u])),this.separableBlurMaterials[u].uniforms.invSize.value=new vt(1/r,1/o),r=Math.round(r/2),o=Math.round(o/2);this.compositeMaterial=this.getCompositeMaterial(this.nMips),this.compositeMaterial.uniforms.blurTexture1.value=this.renderTargetsVertical[0].texture,this.compositeMaterial.uniforms.blurTexture2.value=this.renderTargetsVertical[1].texture,this.compositeMaterial.uniforms.blurTexture3.value=this.renderTargetsVertical[2].texture,this.compositeMaterial.uniforms.blurTexture4.value=this.renderTargetsVertical[3].texture,this.compositeMaterial.uniforms.blurTexture5.value=this.renderTargetsVertical[4].texture,this.compositeMaterial.uniforms.bloomStrength.value=e,this.compositeMaterial.uniforms.bloomRadius.value=.1;let c=[1,.8,.6,.4,.2];this.compositeMaterial.uniforms.bloomFactors.value=c,this.bloomTintColors=[new B(1,1,1),new B(1,1,1),new B(1,1,1),new B(1,1,1),new B(1,1,1)],this.compositeMaterial.uniforms.bloomTintColors.value=this.bloomTintColors;let h=jc;this.copyUniforms=zs.clone(h.uniforms),this.blendMaterial=new je({uniforms:this.copyUniforms,vertexShader:h.vertexShader,fragmentShader:h.fragmentShader,blending:Mc,depthTest:!1,depthWrite:!1,transparent:!0}),this.enabled=!0,this.needsSwap=!1,this._oldClearColor=new se,this.oldClearAlpha=1,this.basic=new Ti,this.fsQuad=new Vs(null)}dispose(){for(let t=0;t<this.renderTargetsHorizontal.length;t++)this.renderTargetsHorizontal[t].dispose();for(let t=0;t<this.renderTargetsVertical.length;t++)this.renderTargetsVertical[t].dispose();this.renderTargetBright.dispose();for(let t=0;t<this.separableBlurMaterials.length;t++)this.separableBlurMaterials[t].dispose();this.compositeMaterial.dispose(),this.blendMaterial.dispose(),this.basic.dispose(),this.fsQuad.dispose()}setSize(t,e){let n=Math.round(t/2),i=Math.round(e/2);this.renderTargetBright.setSize(n,i);for(let r=0;r<this.nMips;r++)this.renderTargetsHorizontal[r].setSize(n,i),this.renderTargetsVertical[r].setSize(n,i),this.separableBlurMaterials[r].uniforms.invSize.value=new vt(1/n,1/i),n=Math.round(n/2),i=Math.round(i/2)}render(t,e,n,i,r){t.getClearColor(this._oldClearColor),this.oldClearAlpha=t.getClearAlpha();let o=t.autoClear;t.autoClear=!1,t.setClearColor(this.clearColor,0),r&&t.state.buffers.stencil.setTest(!1),this.renderToScreen&&(this.fsQuad.material=this.basic,this.basic.map=n.texture,t.setRenderTarget(null),t.clear(),this.fsQuad.render(t)),this.highPassUniforms.tDiffuse.value=n.texture,this.highPassUniforms.luminosityThreshold.value=this.threshold,this.fsQuad.material=this.materialHighPassFilter,t.setRenderTarget(this.renderTargetBright),t.clear(),this.fsQuad.render(t);let a=this.renderTargetBright;for(let l=0;l<this.nMips;l++)this.fsQuad.material=this.separableBlurMaterials[l],this.separableBlurMaterials[l].uniforms.colorTexture.value=a.texture,this.separableBlurMaterials[l].uniforms.direction.value=s.BlurDirectionX,t.setRenderTarget(this.renderTargetsHorizontal[l]),t.clear(),this.fsQuad.render(t),this.separableBlurMaterials[l].uniforms.colorTexture.value=this.renderTargetsHorizontal[l].texture,this.separableBlurMaterials[l].uniforms.direction.value=s.BlurDirectionY,t.setRenderTarget(this.renderTargetsVertical[l]),t.clear(),this.fsQuad.render(t),a=this.renderTargetsVertical[l];this.fsQuad.material=this.compositeMaterial,this.compositeMaterial.uniforms.bloomStrength.value=this.strength,this.compositeMaterial.uniforms.bloomRadius.value=this.radius,this.compositeMaterial.uniforms.bloomTintColors.value=this.bloomTintColors,t.setRenderTarget(this.renderTargetsHorizontal[0]),t.clear(),this.fsQuad.render(t),this.fsQuad.material=this.blendMaterial,this.copyUniforms.tDiffuse.value=this.renderTargetsHorizontal[0].texture,r&&t.state.buffers.stencil.setTest(!0),this.renderToScreen?(t.setRenderTarget(null),this.fsQuad.render(t)):(t.setRenderTarget(n),this.fsQuad.render(t)),t.setClearColor(this._oldClearColor,this.oldClearAlpha),t.autoClear=o}getSeperableBlurMaterial(t){let e=[];for(let n=0;n<t;n++)e.push(.39894*Math.exp(-.5*n*n/(t*t))/t);return new je({defines:{KERNEL_RADIUS:t},uniforms:{colorTexture:{value:null},invSize:{value:new vt(.5,.5)},direction:{value:new vt(.5,.5)},gaussianCoefficients:{value:e}},vertexShader:`varying vec2 vUv;
				void main() {
					vUv = uv;
					gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
				}`,fragmentShader:`#include <common>
				varying vec2 vUv;
				uniform sampler2D colorTexture;
				uniform vec2 invSize;
				uniform vec2 direction;
				uniform float gaussianCoefficients[KERNEL_RADIUS];

				void main() {
					float weightSum = gaussianCoefficients[0];
					vec3 diffuseSum = texture2D( colorTexture, vUv ).rgb * weightSum;
					for( int i = 1; i < KERNEL_RADIUS; i ++ ) {
						float x = float(i);
						float w = gaussianCoefficients[i];
						vec2 uvOffset = direction * invSize * x;
						vec3 sample1 = texture2D( colorTexture, vUv + uvOffset ).rgb;
						vec3 sample2 = texture2D( colorTexture, vUv - uvOffset ).rgb;
						diffuseSum += (sample1 + sample2) * w;
						weightSum += 2.0 * w;
					}
					gl_FragColor = vec4(diffuseSum/weightSum, 1.0);
				}`})}getCompositeMaterial(t){return new je({defines:{NUM_MIPS:t},uniforms:{blurTexture1:{value:null},blurTexture2:{value:null},blurTexture3:{value:null},blurTexture4:{value:null},blurTexture5:{value:null},bloomStrength:{value:1},bloomFactors:{value:null},bloomTintColors:{value:null},bloomRadius:{value:0}},vertexShader:`varying vec2 vUv;
				void main() {
					vUv = uv;
					gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
				}`,fragmentShader:`varying vec2 vUv;
				uniform sampler2D blurTexture1;
				uniform sampler2D blurTexture2;
				uniform sampler2D blurTexture3;
				uniform sampler2D blurTexture4;
				uniform sampler2D blurTexture5;
				uniform float bloomStrength;
				uniform float bloomRadius;
				uniform float bloomFactors[NUM_MIPS];
				uniform vec3 bloomTintColors[NUM_MIPS];

				float lerpBloomFactor(const in float factor) {
					float mirrorFactor = 1.2 - factor;
					return mix(factor, mirrorFactor, bloomRadius);
				}

				void main() {
					gl_FragColor = bloomStrength * ( lerpBloomFactor(bloomFactors[0]) * vec4(bloomTintColors[0], 1.0) * texture2D(blurTexture1, vUv) +
						lerpBloomFactor(bloomFactors[1]) * vec4(bloomTintColors[1], 1.0) * texture2D(blurTexture2, vUv) +
						lerpBloomFactor(bloomFactors[2]) * vec4(bloomTintColors[2], 1.0) * texture2D(blurTexture3, vUv) +
						lerpBloomFactor(bloomFactors[3]) * vec4(bloomTintColors[3], 1.0) * texture2D(blurTexture4, vUv) +
						lerpBloomFactor(bloomFactors[4]) * vec4(bloomTintColors[4], 1.0) * texture2D(blurTexture5, vUv) );
				}`})}};Vo.BlurDirectionX=new vt(1,0);Vo.BlurDirectionY=new vt(0,1);var t0={name:"OutputShader",uniforms:{tDiffuse:{value:null},toneMappingExposure:{value:1}},vertexShader:`
		precision highp float;

		uniform mat4 modelViewMatrix;
		uniform mat4 projectionMatrix;

		attribute vec3 position;
		attribute vec2 uv;

		varying vec2 vUv;

		void main() {

			vUv = uv;
			gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );

		}`,fragmentShader:`
	
		precision highp float;

		uniform sampler2D tDiffuse;

		#include <tonemapping_pars_fragment>
		#include <colorspace_pars_fragment>

		varying vec2 vUv;

		void main() {

			gl_FragColor = texture2D( tDiffuse, vUv );

			// tone mapping

			#ifdef LINEAR_TONE_MAPPING

				gl_FragColor.rgb = LinearToneMapping( gl_FragColor.rgb );

			#elif defined( REINHARD_TONE_MAPPING )

				gl_FragColor.rgb = ReinhardToneMapping( gl_FragColor.rgb );

			#elif defined( CINEON_TONE_MAPPING )

				gl_FragColor.rgb = CineonToneMapping( gl_FragColor.rgb );

			#elif defined( ACES_FILMIC_TONE_MAPPING )

				gl_FragColor.rgb = ACESFilmicToneMapping( gl_FragColor.rgb );

			#elif defined( AGX_TONE_MAPPING )

				gl_FragColor.rgb = AgXToneMapping( gl_FragColor.rgb );

			#elif defined( NEUTRAL_TONE_MAPPING )

				gl_FragColor.rgb = NeutralToneMapping( gl_FragColor.rgb );

			#endif

			// color space

			#ifdef SRGB_TRANSFER

				gl_FragColor = sRGBTransferOETF( gl_FragColor );

			#endif

		}`};var ih=class extends ni{constructor(){super();let t=t0;this.uniforms=zs.clone(t.uniforms),this.material=new Hc({name:t.name,uniforms:this.uniforms,vertexShader:t.vertexShader,fragmentShader:t.fragmentShader}),this.fsQuad=new Vs(this.material),this._outputColorSpace=null,this._toneMapping=null}render(t,e,n){this.uniforms.tDiffuse.value=n.texture,this.uniforms.toneMappingExposure.value=t.toneMappingExposure,(this._outputColorSpace!==t.outputColorSpace||this._toneMapping!==t.toneMapping)&&(this._outputColorSpace=t.outputColorSpace,this._toneMapping=t.toneMapping,this.material.defines={},ge.getTransfer(this._outputColorSpace)===we&&(this.material.defines.SRGB_TRANSFER=""),this._toneMapping===Dd?this.material.defines.LINEAR_TONE_MAPPING="":this._toneMapping===Ud?this.material.defines.REINHARD_TONE_MAPPING="":this._toneMapping===Nd?this.material.defines.CINEON_TONE_MAPPING="":this._toneMapping===qa?this.material.defines.ACES_FILMIC_TONE_MAPPING="":this._toneMapping===Od?this.material.defines.AGX_TONE_MAPPING="":this._toneMapping===Fd&&(this.material.defines.NEUTRAL_TONE_MAPPING=""),this.material.needsUpdate=!0),this.renderToScreen===!0?(t.setRenderTarget(null),this.fsQuad.render(t)):(t.setRenderTarget(e),this.clear&&t.clear(t.autoClearColor,t.autoClearDepth,t.autoClearStencil),this.fsQuad.render(t))}dispose(){this.material.dispose(),this.fsQuad.dispose()}};var Qd="#C8FF3D",Jw="#ECE8DF",ri="#0B0B0B",cs=(s,t,e)=>Math.min(e,Math.max(t,s)),ii=(s,t,e)=>s+(t-s)*e,Ho=s=>s*s*(3-2*s),jd=11,Ir=()=>(jd=jd*16807%2147483647)/2147483647,Ie=(s,t)=>s+Ir()*(t-s),Kw=[["AI Engineer","Hyderabad \xB7 0\u20132 yrs"],["ML Engineer","Bengaluru \xB7 1\u20133 yrs"],["LLM Engineer","Remote India"],["Frontend Engineer","React \xB7 TypeScript"],["Senior AI Engineer","6+ yrs"],["Platform Engineer","Kubernetes"],["Data Analyst","Immediate joiner"],["Sales Executive","Field role"],["Backend Engineer","Berlin \xB7 on-site"],["Product Designer","Mumbai"],["DevOps Engineer","Pune"],["QA Engineer","Chennai"],["Data Scientist","London"],["Support Engineer","Night shift"],["Marketing Lead","Delhi"],["Android Developer","Kochi"]],e0=["#1F3D36","#C2552D","#3B3F8C","#8A6D1F","#5A2A4A","#2E5E86","#6B6B63","#0B0B0B"];function si(s,t,e,n,i,r){s.beginPath(),s.moveTo(t+r,e),s.arcTo(t+n,e,t+n,e+i,r),s.arcTo(t+n,e+i,t,e+i,r),s.arcTo(t,e+i,t,e,r),s.arcTo(t,e,t+n,e,r),s.closePath()}function n0(){let e=document.createElement("canvas");e.width=512*4,e.height=320*4;let n=e.getContext("2d");Kw.forEach(([r,o],a)=>{let l=a%4*512,c=Math.floor(a/4)*320,h=a%7===5;n.save(),n.translate(l,c),n.fillStyle=h?"#1A1A18":Jw,n.fillRect(0,0,512,320);let u=n.createLinearGradient(0,0,512,320);u.addColorStop(0,"rgba(255,255,255,.10)"),u.addColorStop(1,"rgba(0,0,0,.08)"),n.fillStyle=u,n.fillRect(0,0,512,320),n.fillStyle=e0[a%e0.length],si(n,36,36,76,76,16),n.fill(),n.fillStyle="#fff",n.font='700 40px "Bricolage Grotesque", sans-serif',n.textAlign="center",n.fillText(r[0],74,89),n.textAlign="left",n.fillStyle=h?"#8d8d85":"#77756d",n.font='500 19px "Geist Mono", monospace',n.fillText("NO. "+String(a*37+104),132,62),n.fillStyle=h?"#55554f":"#cfcbc0",si(n,132,80,150,12,6),n.fill(),n.fillStyle=h?"#F3F0E8":ri,n.font='700 46px "Bricolage Grotesque", sans-serif',n.fillText(r,36,178),n.fillStyle=h?"#a9a9a0":"#55534c",n.font='500 22px "Geist Mono", monospace',n.fillText(o,36,216),n.fillStyle=h?"#3a3a36":"#d6d2c7",si(n,36,250,130,34,17),n.fill(),si(n,178,250,96,34,17),n.fill(),si(n,392,250,84,34,17),n.fill(),n.restore()});let i=new Do(e);return i.colorSpace=Mn,i.anisotropy=8,i}function Kd(s){let n=document.createElement("canvas");n.width=768,n.height=1056;let i=n.getContext("2d");i.fillStyle="#F6F3EC",i.fillRect(0,0,768,1056);let r=(l,c,h,u=12,f="#D9D5CA")=>{i.fillStyle=f,si(i,l,c,h,u,u/2),i.fill()},o=(l,c,h,u=34)=>{i.fillStyle="rgba(200,255,61,.75)",i.fillRect(l,c,h,u)};if(i.fillStyle=ri,s==="cover"){i.font='500 20px "Geist Mono", monospace',i.fillStyle="#8b887f",i.fillText("COVER LETTER \xB7 UNDER 300 WORDS",64,90),i.fillStyle=ri,i.font='700 54px "Bricolage Grotesque", sans-serif',i.fillText("Dear team,",64,180);let l=240;for(let c=0;c<16;c++){if((c===5||c===11)&&(l+=26),c===8){r(64,l,520,12,"#c9c5ba"),i.strokeStyle="#E2472C",i.lineWidth=5,i.beginPath(),i.moveTo(56,l+6),i.lineTo(596,l+4),i.stroke(),i.fillStyle="#E2472C",i.font='600 18px "Geist Mono", monospace',i.fillText("NOT IN YOUR PROFILE",64,l+44),l+=70;continue}r(64,l,[600,640,560,620,380][c%5]),l+=34}i.fillStyle=ri,i.font='400 44px "Instrument Serif", serif',i.fillText("Asha Rao",64,946)}else{i.font='700 64px "Bricolage Grotesque", sans-serif',i.fillText("Asha Rao",64,124),i.font='500 19px "Geist Mono", monospace',i.fillStyle="#8b887f",i.fillText(s==="cv"?"CURRICULUM VITAE \xB7 WHOLE CAREER":"asha@example.com \xB7 Hyderabad",64,162);let l=(c,h)=>{i.fillStyle="#8b887f",i.font='600 17px "Geist Mono", monospace',i.fillText(h,64,c),i.fillStyle="#cfcbc0",i.fillRect(64,c+12,640,2)};l(230,"EXPERIENCE"),s==="resume"&&o(372,258,248),i.fillStyle=ri,i.font='600 27px "Geist", sans-serif',i.fillText("AI Engineer, Acme Labs",64,284),i.font='500 21px "Geist Mono", monospace',i.fillText("Jun 2024 \u2013 present",380,283),r(64,310,610),r(64,340,540),s==="resume"&&o(64,372,420),i.fillStyle=ri,i.font='500 23px "Geist", sans-serif',i.fillText("Python \xB7 LangChain \xB7 FAISS \xB7 RAG",70,397),r(64,426,580),i.font='600 27px "Geist", sans-serif',i.fillText("ML Intern, Nimbus",64,490),i.font='500 21px "Geist Mono", monospace',i.fillText("Jan \u2013 May 2024",380,489),r(64,516,590),r(64,546,420),l(626,"SKILLS"),r(64,662,140,30,"#E3DFD4"),r(216,662,110,30,"#E3DFD4"),r(338,662,150,30,"#E3DFD4"),r(500,662,120,30,"#E3DFD4"),l(752,s==="cv"?"PROJECTS":"EDUCATION"),r(64,790,520),r(64,820,600),s==="cv"?(r(64,850,480),r(64,880,560),l(940,"CERTIFICATES"),r(64,976,440)):(l(900,"LOCATION"),o(64,926,330),i.fillStyle=ri,i.font='500 23px "Geist", sans-serif',i.fillText("Hyderabad \xB7 not relocating",70,951))}let a=new Do(n);return a.colorSpace=Mn,a.anisotropy=8,a}function Qw(){let e=document.createElement("canvas");e.width=1024,e.height=680;let n=e.getContext("2d"),i=new Do(e);i.colorSpace=Mn,i.anisotropy=8;let r=[["Full name","Asha Rao",.8,2],["Email","asha@example.com",2.5,4],["Phone","+91   98765 43210",4.5,5.6],["College","Example College of Engineering",6,7.4]],o=[[0,700,560],[.8,330,190],[2.5,330,262],[4.5,330,334],[6,330,406],[7.8,330,478],[8.6,190,548],[9.4,190,610],[14,700,560]];return{tex:i,draw:l=>{let c=l%14.5;n.fillStyle="#F4F1EA",n.fillRect(0,0,1024,680),n.fillStyle="#E2DED3",n.fillRect(0,0,1024,64),n.fillStyle="#c4c0b4",[28,54,80].forEach(y=>{n.beginPath(),n.arc(y,32,8,0,7),n.fill()}),n.fillStyle="#F4F1EA",si(n,116,14,620,36,18),n.fill(),n.fillStyle="#77756d",n.font='500 18px "Geist Mono", monospace',n.fillText("careers.example.com/apply/ai-engineer",136,39);let h=c>9&&c<10.6,u=c>8.6&&c<=9;n.fillStyle=h?"#1f7a5c":"#b3541e",n.beginPath(),n.arc(790,32,7,0,7),n.fill(),n.font='600 17px "Geist Mono", monospace',n.fillText(h?"YOU":"AGENT",806,38),n.fillStyle=ri,n.font='700 34px "Bricolage Grotesque", sans-serif',n.fillText("Apply \xB7 AI Engineer",56,124),n.fillStyle="#77756d",n.font='500 18px "Geist", sans-serif',n.fillText("Example Company \xB7 Hyderabad",58,152),r.forEach(([y,v,E,A],T)=>{let R=170+T*72,M=c>=E&&c<A+.3;n.fillStyle="#55534c",n.font='600 18px "Geist", sans-serif',n.fillText(y,56,R+32),n.fillStyle="#fff",si(n,190,R,560,48,10),n.fill(),n.lineWidth=M?3:1.5,n.strokeStyle=M?"#9BD41F":"#d3cfc4",n.stroke();let x=Math.floor(cs((c-E)/(A-E),0,1)*v.length);n.fillStyle=ri,n.font='500 20px "Geist", sans-serif',n.fillText(v.slice(0,x)+(M&&x<v.length?"|":""),206,R+31)}),n.fillStyle="#55534c",n.font='600 18px "Geist", sans-serif',n.fillText("Resume",56,490),n.fillStyle="#fff",si(n,190,458,560,48,10),n.fill(),n.setLineDash(c>8.2?[]:[6,5]),n.strokeStyle="#d3cfc4",n.lineWidth=1.5,n.stroke(),n.setLineDash([]),n.fillStyle=c>8.2?ri:"#9a978d",n.font='500 18px "Geist Mono", monospace',n.fillText(c>8.2?"Asha_Rao_Resume.pdf":"No file chosen",206,489),n.fillStyle="#EDEAE1",si(n,56,524,430,54,10),n.fill(),n.strokeStyle=u||h?"#E08A22":"#d3cfc4",n.lineWidth=u||h?3:1.5,n.stroke(),n.fillStyle="#fff",si(n,72,538,26,26,5),n.fill(),n.strokeStyle="#9a978d",n.lineWidth=1.5,n.stroke(),c>9.8&&(n.strokeStyle="#1f7a5c",n.lineWidth=4,n.beginPath(),n.moveTo(77,551),n.lineTo(84,558),n.lineTo(94,544),n.stroke()),n.fillStyle="#43413b",n.font='500 19px "Geist", sans-serif',n.fillText("I\u2019m not a robot",112,558);let f=c<8.6?null:c<9?["NEEDS YOU","#E08A22"]:c<10.6?["YOU\u2019RE IN CONTROL","#1f7a5c"]:c<12?["GIVEN BACK \xB7 CARRIES ON",ri]:["READY \xB7 YOU REVIEW FIRST",ri];if(f){n.font='600 17px "Geist Mono", monospace';let y=n.measureText(f[0]).width+40;n.fillStyle=f[1],si(n,520,532,y,40,20),n.fill(),n.fillStyle="#fff",n.fillText(f[0],540,558)}n.fillStyle="#EAE6DC",n.fillRect(780,64,244,616),n.fillStyle="#8b887f",n.font='600 14px "Geist Mono", monospace',n.fillText("STEPS",800,100),[["Kit checked",.2],["Type name",2],["Email, phone",5.6],["College \u2260 university",7.4],["Upload resume",8.2],["Needs a person",8.6],["You took over",9],["Given back",10.6],["Ready to review",12]].forEach(([y,v],E)=>{if(c<v)return;let A=118+E*56;n.fillStyle="#F8F6F0",si(n,796,A,212,44,8),n.fill(),n.fillStyle=E===5?"#b3541e":E===6||E===7?"#1f7a5c":"#2a2925",n.font='500 16px "Geist", sans-serif',n.fillText(y,810,A+28)});let d=0;for(;d<o.length-2&&c>o[d+1][0];)d++;let g=o[d],_=o[d+1],m=Ho(cs((c-g[0])/Math.min(.7,_[0]-g[0]),0,1)),p=ii(g[1],_[1],m),S=ii(g[2],_[2],m);n.save(),n.translate(p,S),n.fillStyle=h?"#1f7a5c":Qd,n.strokeStyle=ri,n.lineWidth=2.5,n.lineJoin="round",n.beginPath(),n.moveTo(0,0),n.lineTo(26,20),n.lineTo(14,22),n.lineTo(20,36),n.lineTo(14,39),n.lineTo(8,25),n.lineTo(0,33),n.closePath(),n.fill(),n.stroke(),n.restore(),i.needsUpdate=!0}}}function i0(s,{reduce:t}){let e=/[?&]fast/.test(location.search),n=new Dc({canvas:s,antialias:!1,powerPreference:"high-performance"});n.toneMapping=qa,n.toneMappingExposure=.95;let i=new Lo;i.background=new se("#060606"),i.fog=new Uc("#060606",.03);let r=new Io(n);i.environment=r.fromScene(new Qc,.04).texture,i.environmentIntensity=.5;let o=new bn(35,1,.1,120),a=new Yc("#fff3e2",2.4);a.position.set(-4,6,8),i.add(a);let l=new No(Qd,0,14,1.6);i.add(l);let c=Math.min(innerWidth,innerHeight)<700,h=c?800:1900,u=8,f=30,d=1,g=1,_=!1,m={cx:2.35,cy:0,k:1},p=new Ar,S=1,y=.625,v=.05;p.moveTo(-S/2+v,-y/2),p.lineTo(S/2-v,-y/2),p.quadraticCurveTo(S/2,-y/2,S/2,-y/2+v),p.lineTo(S/2,y/2-v),p.quadraticCurveTo(S/2,y/2,S/2-v,y/2),p.lineTo(-S/2+v,y/2),p.quadraticCurveTo(-S/2,y/2,-S/2,y/2-v),p.lineTo(-S/2,-y/2+v),p.quadraticCurveTo(-S/2,-y/2,-S/2+v,-y/2);let E=new Ya(p,4),A=E.attributes.uv,T=E.attributes.position;for(let K=0;K<A.count;K++)A.setXY(K,T.getX(K)/S+.5,T.getY(K)/y+.5);let R=new Float32Array(h*2),M=new Float32Array(h*2);for(let K=0;K<h;K++){let ft=K<u?[0,1,2,0,1,2,0,1][K]:Math.floor(Ir()*16);R[K*2]=ft%4,R[K*2+1]=3-Math.floor(ft/4)}E.setAttribute("aCell",new Er(R,2));let x=new Er(M,2);x.setUsage(Xd),E.setAttribute("aState",x);let L=new ls({map:n0(),roughness:.5,metalness:0,side:pi});L.onBeforeCompile=K=>{K.vertexShader=K.vertexShader.replace("#include <common>",`#include <common>
attribute vec2 aCell; attribute vec2 aState; varying vec2 vState; varying vec2 vLoc;`).replace("#include <uv_vertex>",`#include <uv_vertex>
vLoc = uv; vState = aState; vMapUv = (uv + aCell) * .25;`),K.fragmentShader=K.fragmentShader.replace("#include <common>",`#include <common>
varying vec2 vState; varying vec2 vLoc;`).replace("#include <map_fragment>",`#include <map_fragment>
if(!gl_FrontFacing) diffuseColor.rgb = vec3(.035);
diffuseColor.rgb *= mix(1., .16, vState.y);`).replace("#include <emissivemap_fragment>",`#include <emissivemap_fragment>
float ed = min(min(vLoc.x,1.-vLoc.x)*1.6, min(vLoc.y,1.-vLoc.y));
float rim = 1.-smoothstep(.0,.07,ed);
totalEmissiveRadiance += vec3(.58,1.,.045) * vState.x * (rim*1.5 + .02) + diffuseColor.rgb * vState.x * .05;`)};let U=new Nc(E,L,h);U.frustumCulled=!1,U.instanceMatrix.setUsage(Xd),i.add(U);let F=new mi,z=new wi,q=9,H=()=>({p:new Float32Array(h*3),q:new Float32Array(h*4),s:new Float32Array(h),g:new Float32Array(h),d:new Float32Array(h),amp:.1}),W=[],V=(K,ft,Ut,J,ht,Tt,ct,Nt,Et,Ht=0,fe=0,jt="XYZ")=>{K.p[ft*3]=Ut,K.p[ft*3+1]=J,K.p[ft*3+2]=ht,z.setFromEuler(F.set(Tt,ct,Nt,jt)),z.toArray(K.q,ft*4),K.s[ft]=Et,K.g[ft]=Ht,K.d[ft]=fe},st=new Float32Array(h*7),I=new Float32Array(h),at=new Float32Array(h),Dt=new Float32Array(h*3);for(let K=0;K<h;K++)st.set([Ie(-36,36),Ie(-18,18),Ie(-48,-16),Ie(-.6,.6),Ie(-.9,.9),Ie(-.5,.5),Ie(.9,1.5)],K*7),I[K]=Ir(),at[K]=Ir()*6.28,Dt.set([Ie(-1,1),Ie(-1,1),Ie(-1,1)],K*3);let Vt=(K,ft,Ut=.55)=>V(K,ft,st[ft*7],st[ft*7+1],st[ft*7+2],st[ft*7+3],st[ft*7+4],st[ft*7+5],st[ft*7+6],0,Ut);function Z(){jd=97;let{cx:K,cy:ft,k:Ut}=m;W=Array.from({length:q},H),W[0].amp=.5;for(let J=0;J<h;J++){let ht=7.5+Math.pow(Ir(),.8)*19,Tt=Ir()*6.283;V(W[0],J,Math.cos(Tt)*ht,Ie(-10,10),Math.sin(Tt)*ht-4,Ie(-3,3),Ie(-3,3),Ie(-3,3),Ie(.8,1.7),0,Ir()<.5?.25:0)}{let ht=Math.round(Math.sqrt(h/3.4)),Tt=Math.ceil(h/ht),ct=1.1/15;W[1].amp=.03;for(let Nt=0;Nt<h;Nt++){let Et=Nt%Tt,Ht=Math.floor(Nt/Tt),fe=(Et-(Tt-1)/2)*ct;V(W[1],Nt,Math.sin(fe)*15,(Ht-(ht-1)/2)*.72,7-Math.cos(fe)*15,0,-fe,0,1,0,.42)}}{W[2].amp=.12;let J=[[.5,.2],[-.35,-.5],[.15,.9]];for(let ht=0;ht<h;ht++){let Tt=ht%3,ct=(3.1+Tt*1.15+Ie(-.12,.12))*Ut,Nt=ht/h*6.283*(7+Tt*2)+Tt,[Et,Ht]=J[Tt],fe=Math.cos(Nt)*ct,jt=Ie(-.12,.12),_e=Math.sin(Nt)*ct,Ue=jt*Math.cos(Et)-_e*Math.sin(Et),de=jt*Math.sin(Et)+_e*Math.cos(Et),pe=fe*Math.cos(Ht)-Ue*Math.sin(Ht),ae=fe*Math.sin(Ht)+Ue*Math.cos(Ht);V(W[2],ht,K+pe,ft+ae,de-.5,Et,-Nt+1.57,Ht,.3*Ut,0,.3)}}{W[3].amp=.05;for(let J=0;J<h;J++){let ht=J/h,Tt=J%6,ct=Tt*1.047+ht*3.2+Ie(-.16,.16),Nt=2.7+ht*2.2+Ie(-.15,.15);V(W[3],J,Math.cos(ct)*Nt,Math.sin(ct)*Nt,6-ht*52,0,-1.571+.55,ct,.95,0,Tt%2?.5:.12,"ZYX")}}for(let J=0;J<h;J++)if(J<u){let ht=J%2,Tt=Math.floor(J/2);V(W[4],J,K+(ht-.5)*1.16*Ut+Tt%2*.08,ft+(1.5-Tt)*.76*Ut,.6-Tt*.1,0,-.22,(ht-.5)*.03,1.02*Ut,J===0?1:.55,0)}else Vt(W[4],J,.86);for(let J=0;J<h;J++)J===0?V(W[5],J,K-1.75*Ut,ft+1.42*Ut,1.2,0,.1,-.06,.78*Ut,1,0):Vt(W[5],J,.86);for(let J=0;J<h;J++)Vt(W[6],J,.84);{let J=[7,6,6,4,2,5],ht=0,Tt=[];J.forEach((ct,Nt)=>{for(let Et=0;Et<ct;Et++)Tt.push([Nt,Et])});for(let ct=0;ct<h;ct++){if(ct<f){let[Nt,Et]=Tt[ct===0?13:ct<=13?ct-1:ct];V(W[7],ct,(Nt-2.5)*1.12*Ut+(_?0:1.2),ft+2.05*Ut-Et*.7*Ut,-Et*.22+.2,-.3,_?0:-.2,0,.98*Ut,ct===0?1:0,Nt===5?.5:0)}else Vt(W[7],ct,.86);ht++}}{W[8].amp=.06;for(let J=0;J<h;J++){let ht=Ie(-1,1),Tt=J%2,ct=4.3*Ut;V(W[8],J,ht*ct+Ie(-.35,.35),(Tt?-ht:ht)*ct+Ie(-.35,.35)+(_?1.2:0),Ie(-1.4,1.2)-1,Ie(-.5,.5),Ie(-.5,.5),Ie(-.6,.6),Ie(.3,.55),Tt?.5:0,Tt?0:.5)}}}let rt=(K,ft)=>{let Ut=new Tr(K,ft,14,1),J=Ut.attributes.position;for(let ht=0;ht<J.count;ht++){let Tt=J.getX(ht)/K;J.setZ(ht,-Tt*Tt*.22)}return Ut.computeVertexNormals(),Ut},St=K=>new ve(rt(1.56,2.14),new ls({map:Kd(K),roughness:.82,color:"#c9c7c2",side:pi})),ot=St("resume");i.add(ot);let Rt=new ve(new Tr(1.7,.022),new Ti({color:new se(Qd).multiplyScalar(2.2),toneMapped:!1,transparent:!0}));i.add(Rt);let Bt=["resume","cover","cv"].map(K=>{let ft=St(K);return i.add(ft),ft}),Wt=Qw(),Xt=new Ns;i.add(Xt);let et=(K,ft,Ut)=>{let J=new Ar;return J.moveTo(-K/2+Ut,-ft/2),J.lineTo(K/2-Ut,-ft/2),J.quadraticCurveTo(K/2,-ft/2,K/2,-ft/2+Ut),J.lineTo(K/2,ft/2-Ut),J.quadraticCurveTo(K/2,ft/2,K/2-Ut,ft/2),J.lineTo(-K/2+Ut,ft/2),J.quadraticCurveTo(-K/2,ft/2,-K/2,ft/2-Ut),J.lineTo(-K/2,-ft/2+Ut),J.quadraticCurveTo(-K/2,-ft/2,-K/2+Ut,-ft/2),J},nt=new ve(new Vc(et(4.36,2.94,.14),{depth:.08,bevelEnabled:!0,bevelSize:.02,bevelThickness:.02,bevelSegments:3}),new ls({color:"#141414",roughness:.32,metalness:.85}));nt.position.z=-.11,Xt.add(nt);let P=new Ya(et(4.2,2.79,.08),6);{let K=P.attributes.uv,ft=P.attributes.position;for(let Ut=0;Ut<K.count;Ut++)K.setXY(Ut,ft.getX(Ut)/4.2+.5,ft.getY(Ut)/2.79+.5)}let It=new ve(P,new Ti({map:Wt.tex,color:"#b8b8b8"}));Xt.add(It);let lt=new un(1,1,{samples:c||e?0:4,type:ei}),O=new eh(n,lt);O.addPass(new nh(i,o));let dt=new Vo(new vt(1,1),.32,.6,1);e||O.addPass(dt);let zt=new zo({uniforms:{tDiffuse:{value:null},uT:{value:0}},vertexShader:"varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.); }",fragmentShader:"uniform sampler2D tDiffuse; uniform float uT; varying vec2 vUv; void main(){ vec2 c=vUv-.5; float d=dot(c,c); vec2 o=c*d*.006; vec3 col=vec3(texture2D(tDiffuse,vUv+o).r,texture2D(tDiffuse,vUv).g,texture2D(tDiffuse,vUv-o).b); col*=1.-d*1.15; float n=fract(sin(dot(vUv*vec2(1731.,977.)+fract(uT)*37.,vec2(12.9898,78.233)))*43758.5453); col+=(n-.5)*.03*(.4+col.g); gl_FragColor=vec4(col,1.); }"});O.addPass(zt),O.addPass(new ih);function At(){d=s.clientWidth||innerWidth,g=s.clientHeight||innerHeight;let K=Math.min(devicePixelRatio||1,c?1.5:1.6)*C;n.setPixelRatio(K),n.setSize(d,g,!1),O.setPixelRatio(K),O.setSize(d,g),o.aspect=d/g;let ft=d/g<.85;o.fov=ft?52:35,o.updateProjectionMatrix();let Ut=ft?{cx:0,cy:1.9,k:.8}:{cx:d/g<1.35?1.7:2.35,cy:0,k:d/g<1.35?.82:1};(ft!==_||Ut.cx!==m.cx||!W.length)&&(_=ft,m=Ut,Z())}let C=e?.5:1;At(),addEventListener("resize",At);let b=[[0,0,9,0],[0,0,7,0],[0,0,9,0],[0,0,8,-20],[0,0,9,0],[0,0,9,0],[0,0,9,0],[0,.2,9.6,0],[0,0,10.5,0]],X=new Ce,Q=new B,it=new B,j=[0,0,0,1],xt=0,pt=0,bt=0,Kt=0,ut=0,gt=0,qt=0,Yt=0,Lt=!1,ee=!0,Jt=0,Qt=0,D=0,yt=0,$=0;addEventListener("pointermove",K=>{let ft=K.clientX/innerWidth*2-1;Yt+=(ft-bt)*.5,bt=ft,Kt=K.clientY/innerHeight*2-1},{passive:!0});let tt=K=>cs(1-Math.abs(pt-K)*1.5,0,1);function Mt(K){if(!ee||document.hidden){Lt=!1;return}requestAnimationFrame(Mt);let ft=Math.min(.05,(K-Jt)/1e3||.016);Jt=K,t||(Qt+=ft),pt+=(xt-pt)*(t||e||/[?&]snap/.test(location.search)?1:Math.min(1,ft*3.2)),Math.abs(xt-pt)<4e-4&&(pt=xt);let Ut=cs(Math.floor(pt),0,q-2),J=cs(pt-Ut,0,1),ht=W[Ut],Tt=W[Ut+1],ct=U.instanceMatrix.array,Nt=ii(ht.amp,Tt.amp,J);for(let w=0;w<h;w++){let N=Ho(cs(J*1.7-I[w]*.7,0,1)),G=w*3,Y=Math.sin(Math.PI*N)*1.6,k=Qt*.5+at[w];Q.set(ii(ht.p[G],Tt.p[G],N)+Dt[G]*Y+Math.sin(k)*Nt,ii(ht.p[G+1],Tt.p[G+1],N)+Dt[G+1]*Y+Math.cos(k*.8)*Nt,ii(ht.p[G+2],Tt.p[G+2],N)+Dt[G+2]*Y),wi.slerpFlat(j,0,ht.q,w*4,Tt.q,w*4,N),z.fromArray(j);let mt=ii(ht.s[w],Tt.s[w],N);it.set(mt,mt,mt),X.compose(Q,z,it).toArray(ct,w*16);let _t=ii(ht.g[w],Tt.g[w],N);M[w*2]=_t*(.82+.18*Math.sin(Qt*2+at[w])),M[w*2+1]=ii(ht.d[w],Tt.d[w],N)}U.instanceMatrix.needsUpdate=!0,x.needsUpdate=!0,Yt*=.94,qt+=Yt*ft*2,qt*=.995;let Et=cs(1-pt,0,1),Ht=cs(pt-7,0,1);U.rotation.y=(Math.sin(Qt*.07)*.35+Qt*.012+qt)*Et+Math.sin(Qt*.25)*.12*Ht,U.rotation.x=Kt*.04*Et;let fe=b[Ut],jt=b[Ut+1],_e=Ho(J),Ue=_?1.45:1;ut+=(bt*.55-ut)*Math.min(1,ft*2.5),gt+=(-Kt*.32-gt)*Math.min(1,ft*2.5),o.position.set(ii(fe[0],jt[0],_e)+ut,ii(fe[1],jt[1],_e)+gt+(_?.4:0),ii(fe[2],jt[2],_e)*Ue-(Ut===3?J*2.5:0)-(Ut===2?J*1:0)),o.lookAt(ut*.2,(_?.4:0)+gt*.2,ii(fe[3],jt[3],_e));let{cx:de,cy:pe,k:ae}=m,Ye=Ho(tt(2));if(ot.visible=Rt.visible=Ye>.002,ot.visible){ot.position.set(de,pe-(1-Ye)*5+Math.sin(Qt*.8)*.04,.2),ot.rotation.set(-.05+(1-Ye)*1.2,-.28+Math.sin(Qt*.5)*.05,.04-(1-Ye)*.6),ot.scale.setScalar(1.4*ae);let w=Math.sin(Qt*1.1)*.9;Rt.position.set(de-.02,pe+w*ae*1.4,.55),Rt.rotation.y=-.28,Rt.scale.set(ae*1.4,1,1),Rt.material.opacity=Ye*Ye}let Re=tt(5);Bt.forEach((w,N)=>{let G=Ho(cs(Re*1.5-N*.2,0,1));w.visible=G>.002,w.visible&&(w.position.set(de-.25*ae+(N-1)*1.08*ae,pe-.25*ae-(1-G)*5+Math.sin(Qt*.7+N)*.035,N===1?.55:.1),w.rotation.set(-.04+(1-G)*.9,-.2+(N-1)*-.14,(1-N)*.07+(1-G)*(N-1)*.5),w.scale.setScalar(.96*ae))});let qe=Ho(tt(6));Xt.visible=qe>.002,Xt.visible&&(Xt.position.set(_?0:de-.8,pe+(_?.1:0)-(1-qe)*5.5+Math.sin(Qt*.6)*.05,.4),Xt.rotation.set(.03+(1-qe)*.5,(_?0:-.36)+Math.sin(Qt*.4)*.03+ut*.08,(1-qe)*-.2),Xt.scale.setScalar((_?.62:.98)*(d/g<1.35&&!_?.8:1)),$+=ft,$>.07&&($=0,Wt.draw(t?12.5:Qt))),l.position.set(de,pe,2.5),l.intensity=(tt(4)+tt(5)*.5+Ht*.6)*5,zt.uniforms.uT.value=Qt,O.render(),yt++,ft>.034&&D++,yt===80&&(D>44&&C>.55&&(C-=.2,At()),yt=0,D=0)}let wt=()=>{!Lt&&ee&&(Lt=!0,Jt=performance.now(),requestAnimationFrame(Mt))};return document.addEventListener("visibilitychange",wt),{setP(K){xt=K},setActive(K){ee=K,K&&wt()},refresh(){L.map.dispose(),L.map=n0(),L.needsUpdate=!0,ot.material.map=Kd("resume"),Bt.forEach((K,ft)=>K.material.map=Kd(["resume","cover","cv"][ft]))}}}Le.registerPlugin(ie,Gl);var $t=(s,t=document)=>t.querySelector(s),on=(s,t=document)=>[...t.querySelectorAll(s)],Ci=matchMedia("(prefers-reduced-motion: reduce)").matches,c0=matchMedia("(hover:hover) and (pointer:fine)").matches,rh=(s,t,e)=>Math.min(e,Math.max(t,s)),tp=s=>new Promise(t=>setTimeout(t,s)),np=(()=>{let s=document.createElement("div");return s.setAttribute("aria-live","polite"),s.style.cssText="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)",document.body.appendChild(s),t=>{s.textContent="",setTimeout(()=>s.textContent=t,60)}})(),us=null;Ci||(us=new vg({lerp:.1,wheelMultiplier:1}),us.on("scroll",ie.update),Le.ticker.add(s=>us.raf(s*1e3)),Le.ticker.lagSmoothing(0));var jw=s=>{us?us.scrollTo(s,{offset:0,duration:1.4}):s.scrollIntoView()};document.addEventListener("click",s=>{let t=s.target.closest('a[href^="#"]');if(!t)return;let e=document.getElementById(t.getAttribute("href").slice(1));e&&(s.preventDefault(),rp(),jw(e),e.setAttribute("tabindex","-1"),e.focus({preventScroll:!0}))});var Gs=(()=>{let s=(navigator.userAgentData&&navigator.userAgentData.platform||navigator.platform||"")+" "+navigator.userAgent;return/android|iphone|ipad|ipod/i.test(s)?"mobile":/win/i.test(s)?"win":/mac/i.test(s)?"mac":/linux|x11|cros/i.test(s)?"lin":null})(),oh={win:"Windows",mac:"macOS",lin:"Linux"};oh[Gs]&&($t("#heroDlT").textContent="Download for "+oh[Gs],on(".os em").forEach(s=>s.classList.toggle("on",s.dataset.r===Gs)));var Lr=$t("#menu"),Go=$t("#burger");function rp(){Lr.hidden||(Lr.hidden=!0,Go.setAttribute("aria-expanded","false"),Go.setAttribute("aria-label","Open menu"),us&&us.start())}Go.addEventListener("click",()=>{if(!Lr.hidden)return rp();Lr.hidden=!1,Go.setAttribute("aria-expanded","true"),Go.setAttribute("aria-label","Close menu"),us&&us.stop(),Le.from(Lr.children,{yPercent:60,opacity:0,duration:.8,ease:"expo.out",stagger:.05}),$t("a",Lr).focus()});addEventListener("keydown",s=>{s.key==="Escape"&&(rp(),Go.focus())});var hs=null;try{hs=i0($t("#gl"),{reduce:Ci})}catch(s){console.warn("WebGL unavailable",s),document.documentElement.classList.add("nogl")}var Ja=on(".chap"),h0=$t("#story"),u0=$t("#fin"),s0=$t("#nav"),$a=[],ip=[],ep=0,op=()=>{$a=Ja.map(s=>s.offsetTop+h0.offsetTop),ip=Ja.map(s=>s.offsetHeight)};function ap(){let s=scrollY,t=innerHeight,e=0;for(let o=0;o<Ja.length;o++)s>=$a[o]&&(e=o);let n=rh((s-$a[e])/Math.max(1,ip[e]-t),0,1),i=rh((n-.5)/.5,0,1),r=e+(e<Ja.length-1?i*i*(3-2*i):0);u0.getBoundingClientRect().top<t*.75&&(r=8),hs&&hs.setP(r),Ja.forEach((o,a)=>o.classList.toggle("on",s>$a[a]-t*.45&&s<$a[a]+ip[a]-t*.55)),s0.classList.toggle("hide",s>t&&s>ep+3&&Lr.hidden),s<ep-3&&s0.classList.remove("hide"),ep=s}op();addEventListener("resize",()=>{op(),ap()});addEventListener("scroll",ap,{passive:!0});ap();if(hs){let s=new Set,t=new IntersectionObserver(e=>{e.forEach(n=>n.isIntersecting?s.add(n.target):s.delete(n.target)),hs.setActive(s.size>0)});t.observe(h0),t.observe(u0)}var tT=on(".nav ul a");["story","try","inside","screens","source","faq"].forEach(s=>new IntersectionObserver(t=>t.forEach(e=>{e.isIntersecting&&tT.forEach(n=>n.getAttribute("href")==="#"+s?n.setAttribute("aria-current","true"):n.removeAttribute("aria-current"))}),{rootMargin:"-45% 0px -50% 0px"}).observe(document.getElementById(s)));var r0=on(".hero .ln").map(s=>{let t=document.createElement("span");for(t.style.display="block";s.firstChild;)t.appendChild(s.firstChild);return s.appendChild(t),t});(async()=>{let s=$t("#pre"),t=$t("#preN"),e=$t("#preB"),n={v:0},i=document.fonts?Promise.all(['700 40px "Bricolage Grotesque"','500 20px "Geist"','500 20px "Geist Mono"','italic 40px "Instrument Serif"'].map(a=>document.fonts.load(a))).catch(()=>{}):Promise.resolve();if(Ci){await i,hs&&hs.refresh(),s.remove(),o0();return}Le.set(r0,{yPercent:115}),Le.set(".hero-b > *, .hero-meta, .scroll-cue",{opacity:0,y:24});let r=Le.to(n,{v:100,duration:1.5,ease:"power2.inOut",onUpdate(){t.textContent=String(Math.round(n.v)).padStart(2,"0"),e.style.transform=`scaleX(${n.v/100})`}});await Promise.all([i,r]),hs&&hs.refresh(),Le.timeline().to(".pre-in > *",{yPercent:-120,duration:.7,ease:"expo.in",stagger:.05}).to(s,{yPercent:-100,duration:1,ease:"expo.inOut",onComplete:()=>s.remove()},"-=.25").to(r0,{yPercent:0,duration:1.4,ease:"expo.out",stagger:.12},"-=.45").to(".hero-b > *, .hero-meta, .scroll-cue",{opacity:1,y:0,duration:1,ease:"expo.out",stagger:.08},"-=.9"),o0()})();function o0(){op(),ie.refresh(),!Ci&&(on("[data-split]").forEach(s=>Gl.create(s,{type:"lines",mask:"lines",linesClass:"sl",autoSplit:!0,onSplit:t=>Le.from(t.lines,{yPercent:115,duration:1.2,ease:"expo.out",stagger:.1,scrollTrigger:{trigger:s,start:"top 88%",once:!0}})})),Le.utils.toArray(".head .lede, .panel, .feat li, .case, .truth div, .qa details, .steps > li, .osp, .os button, .stack .lv, .ag-grid div").forEach(s=>Le.from(s,{y:50,opacity:0,duration:1.1,ease:"expo.out",scrollTrigger:{trigger:s,start:"top 92%",once:!0}})))}c0&&!Ci&&(on(".mag").forEach(s=>{let t=Le.quickTo(s,"x",{duration:.6,ease:"expo.out"}),e=Le.quickTo(s,"y",{duration:.6,ease:"expo.out"});s.addEventListener("pointermove",n=>{let i=s.getBoundingClientRect();t((n.clientX-i.left-i.width/2)*.3),e((n.clientY-i.top-i.height/2)*.4)}),s.addEventListener("pointerleave",()=>{t(0),e(0)})}),on(".tilt").forEach(s=>{let t=Le.quickTo(s,"rotationX",{duration:.8,ease:"expo.out"}),e=Le.quickTo(s,"rotationY",{duration:.8,ease:"expo.out"});s.addEventListener("pointermove",n=>{let i=s.getBoundingClientRect(),r=(n.clientX-i.left)/i.width,o=(n.clientY-i.top)/i.height;e((r-.5)*9),t((.5-o)*7),s.style.setProperty("--mx",r*100+"%"),s.style.setProperty("--my",o*100+"%")}),s.addEventListener("pointerleave",()=>{t(0),e(0)})}));var sh=[{n:"AI Engineer",s:"0\u20132 yrs \xB7 Hyderabad",fit:93,v:"Strong match",seen:75,sv:"Good chance \u2014 4 days old, on the company\u2019s own board",c:[["Career track","ok","Same track: GenAI / LLM engineering"],["Experience","ok","0\u20132 years asked; you have ~1.6"],["Location","ok","Hyderabad \u2014 where you live"],["Must-haves","ok","Python, LLMs, RAG \u2014 all shown at work"],["Notice","unk","Not stated \u2014 kept as unknown"]]},{n:"Senior AI Engineer",s:"6+ yrs \xB7 same skills",fit:22,v:"Incompatible",seen:30,sv:"Low chance \u2014 public listing, three weeks old",cap:"A failed hard check caps the score. Identical skills don\u2019t lift it.",c:[["Career track","ok","Same track"],["Experience","fail","Requires 6+ years; you have ~1.6"],["Location","ok","Hyderabad"],["Must-haves","ok","All shown at work"],["Notice","unk","Not stated"]]},{n:"Frontend Engineer",s:"React \xB7 TypeScript",fit:12,v:"Incompatible",seen:60,sv:"Fair chance \u2014 fresh, but a crowded public board",cap:"Different career track. Keyword overlap can\u2019t make it a fit.",c:[["Career track","fail","Frontend, not AI/ML engineering"],["Experience","ok","Years fit"],["Location","ok","Remote allowed"],["Must-haves","fail","React, TypeScript \u2014 not in your profile"],["Notice","ok","30 days accepted"]]},{n:"AI Engineer",s:"Kubernetes mandatory",fit:31,v:"Incompatible",seen:70,sv:"Good chance \u2014 company board, this week",cap:"A short, explicit must-have still rules a job out.",c:[["Career track","ok","Same track"],["Experience","ok","1\u20133 years asked"],["Location","ok","Hyderabad, hybrid"],["Must-haves","fail","Mandatory: Kubernetes \u2014 not in your profile"],["Notice","ok","30 days accepted"]]},{n:"AI Engineer",s:"Berlin \xB7 on-site",drop:1,c:[["Country","fail","Outside India \u2014 dropped before scoring. It never takes a result slot and costs no AI call."]]}];(()=>{let s=$t("#roles");s.innerHTML=sh.map((i,r)=>`<button type="button" role="radio" aria-checked="${!r}" tabindex="${r?-1:0}">${i.n}<small>${i.s}</small></button>`).join("");let t=on("button",s),e={f:0,s:0},n=i=>{let r=sh[i];t.forEach((c,h)=>{c.setAttribute("aria-checked",h===i),c.tabIndex=h===i?0:-1});let o=r.drop?0:r.fit,a=r.drop?0:r.seen;Le.to(e,{f:o,s:a,duration:Ci?0:1.1,ease:"expo.out",onUpdate(){$t("#fitN").textContent=r.drop?"\u2014":Math.round(e.f),$t("#seenN").textContent=r.drop?"\u2014":Math.round(e.s)}}),$t("#fitB").style.transform=`scaleX(${o/100})`,$t("#seenB").style.transform=`scaleX(${a/100})`,$t("#fitV").textContent=r.drop?"Dropped \u2014 not scored":r.v,$t("#seenV").textContent=r.drop?"Not measured":r.sv,$t("#fitN").parentElement.dataset.t=o<60?"bad":"ok",$t("#seenN").parentElement.dataset.t=r.drop?"bad":"ok",$t("#checks").innerHTML=r.c.map(([c,h,u])=>`<li data-s="${h}"><b>${c}</b><span>${u}</span></li>`).join(""),Ci||Le.from("#checks li",{opacity:0,x:-14,duration:.6,ease:"expo.out",stagger:.05});let l=$t("#capN");l.hidden=!r.cap,l.textContent=r.cap||""};t.forEach((i,r)=>{i.addEventListener("click",()=>n(r)),i.addEventListener("keydown",o=>{let a={ArrowRight:1,ArrowDown:1,ArrowLeft:-1,ArrowUp:-1}[o.key];if(a){o.preventDefault();let l=(r+a+sh.length)%sh.length;n(l),t[l].focus()}})}),ie.create({trigger:"#mx",start:"top 80%",once:!0,onEnter:()=>n(0)})})();(()=>{let s=$t("#brw"),t=$t("#pg"),e=$t("#cur"),n=$t("#log"),i=$t("#agS"),r=$t("#banner"),o={go:$t("#aGo"),stop:$t("#aStop"),take:$t("#aTake"),give:$t("#aGive")},a={name:$t("#fN"),email:$t("#fE"),phone:$t("#fP")},l=$t("#cap"),c=$t("#capB"),h=$t("#fF"),u="idle",f=0,d="running",g=(E,A)=>{u=E,i.textContent=A||{idle:"Ready",running:"Agent working",stopped:"Stopped \xB7 saved",you:"You\u2019re in control",needs:"Needs you",done:"Done \xB7 nothing sent"}[E],i.dataset.s=E,s.dataset.mode=E==="you"?"you":"agent",$t("#who").textContent=E==="you"?"YOU":"AGENT",o.stop.disabled=!(E==="running"||E==="needs"),o.take.disabled=!(E==="running"||E==="needs"||E==="stopped"),o.give.disabled=E!=="you",o.go.disabled=!(E==="idle"||E==="stopped"||E==="done"),o.go.textContent=E==="stopped"?"Continue":E==="done"?"Run again":"Start",o.take.classList.toggle("hot",E==="needs"),o.give.classList.toggle("hot",E==="you"),o.go.classList.toggle("hot",!o.go.disabled);let T=E==="you";Object.values(a).forEach(R=>R.readOnly=!T),c.disabled=!T,r.classList.toggle("show",T)},_=(E,A="",T="")=>{let R=document.createElement("li");R.className=T,R.innerHTML=E+(A?`<small>${A}</small>`:""),n.appendChild(R),n.scrollTop=n.scrollHeight},m=async E=>{let A=f;for(await tp(Ci?Math.min(E,30):E);u!=="running";){if(A!==f)throw 0;await tp(120)}if(A!==f)throw 0},p=async E=>{let A=t.getBoundingClientRect(),T=E.getBoundingClientRect();e.style.transform=`translate(${T.left-A.left+Math.min(46,T.width/2)}px,${T.top-A.top+T.height/2}px)`,await m(750)},S=E=>on(".fl",t).forEach(A=>A.classList.toggle("f",A.dataset.f===E)),y=async(E,A)=>{E.value="";for(let T of A)E.value+=T,await m(36)};async function v(){let E=++f;try{for(n.innerHTML="",Object.values(a).forEach(A=>A.value=""),c.checked=!1,h.textContent="No file chosen",h.classList.remove("done"),l.classList.remove("show","need"),e.style.transform="translate(24px,24px)",g("running"),_("Kit checked","resume \xB7 cover letter \xB7 CV"),await m(500),S("name"),await p(a.name),await y(a.name,"Asha Rao"),_("Fill in name"),S("email"),await p(a.email),await y(a.email,"asha@example.com"),S("phone"),await p(a.phone),await y(a.phone,"98765 43210"),_("Email and phone","+91 in its own picker"),S("file"),await p(h),h.textContent="Asha_Rao_Resume.pdf",h.classList.add("done"),_("Attach the resume"),await m(300),S(""),l.classList.add("show"),await p(l),l.classList.add("need"),g("needs"),_("A \u201Cnot a robot\u201D check needs a person","press Take over","need"),np("The agent needs you. Take over to complete the check.");!(c.checked&&u==="running");){if(E!==f)throw 0;u==="running"&&!c.checked&&(g("needs"),_("Still waiting for the check","","need")),await tp(150)}l.classList.remove("need"),await m(300),_("Carried on from where you left it","progress kept"),await m(500),g("done"),_("Ready to submit. In the app the agent submits, or you press \u201CI submitted it\u201D.","demo ends here"),np("Demo finished. Nothing was sent.")}catch{}}o.go.addEventListener("click",()=>{u==="stopped"?(g(d),_("Continue","from the last page")):v()}),o.stop.addEventListener("click",()=>{d=u,g("stopped"),_("Stopped at once","steps saved")}),o.take.addEventListener("click",()=>{u!=="stopped"&&(d=u),g("you"),_("You took over","your clicks go to the page","you"),(l.classList.contains("show")?c:a.name).focus({preventScroll:!0})}),o.give.addEventListener("click",()=>{g("running"),_("Given back to the agent","","you")}),g("idle")})();if(!Ci&&innerWidth>760){let s=$t("#pipeT"),t=()=>s.scrollWidth-innerWidth;Le.to(s,{x:()=>-t(),ease:"none",scrollTrigger:{trigger:"#pipe",pin:!0,scrub:.8,end:()=>"+="+t(),invalidateOnRefresh:!0}})}if(c0){let s=$t("#peek"),t=$t("#peekI"),e=Le.quickTo(s,"x",{duration:.7,ease:"expo.out"}),n=Le.quickTo(s,"y",{duration:.7,ease:"expo.out"});on("#feat li").forEach(i=>{new Image().src=`assets/shots/${i.dataset.img}.webp`,i.addEventListener("pointerenter",()=>{t.src=`assets/shots/${i.dataset.img}.webp`,Le.to(s,{opacity:1,scale:1,duration:.6,ease:"expo.out"})}),i.addEventListener("pointerleave",()=>Le.to(s,{opacity:0,scale:.6,duration:.4,ease:"power3.in"})),i.addEventListener("pointermove",r=>{let o=s.offsetWidth;e(rh(r.clientX+30,10,innerWidth-o-10)),n(rh(r.clientY-s.offsetHeight*.55,10,innerHeight-s.offsetHeight-10))})})}(()=>{let s={web:["web/","Preact + htm","The app you see","The interface in your browser or desktop window: Preact with htm and bundled fonts, no build step. Light and dark themes, keyboard friendly, live progress."],api:["api/","FastAPI \xB7 WebSockets","The front desk","FastAPI routes and two WebSockets: one streams live search events, the other streams the Auto-apply browser into the app. Rate limits on every AI endpoint."],services:["services/","orchestration","The foreman","Runs searches, the watchlist watcher, documents, profiles and the Auto-apply kit. One search at a time; every event carries its run id."],intelligence:["intelligence/","understand \xB7 judge","Understanding & judgement","Reads the candidate and each job, matches with hard checks first, scores reach, finds people to contact, and learns skill links. Weights live in one tunable policy file."],discovery:["discovery/","find \xB7 verify","Finding real jobs","Search, adapters for Greenhouse, Lever, Ashby, SmartRecruiters, Recruitee, Workable, Workday, Oracle and Keka, page parsing, dedupe, validation, and SSRF-safe fetching."],generation:["generation/","write \xB7 fact-check","Honest documents","Resume, CV and cover letter; fact-checking every AI line against your profile; five styles; a chat editor whose edits are whitelisted and checked; PDF rendering."],agents:["agents/","browser","The browser agent","Runs an Auto-apply session (stop, take over, continue, close) on one thread that owns the browser, and streams Chrome\u2019s screencast into the app."],config:["config/","LLM router","The model router","Every AI call goes through a task chain: the first usable model answers, the next takes over if one is busy, rate-limited or rejected. Works with Google AI Studio, NVIDIA NIM, Groq, Mistral and Kilo."],tools:["tools/","search \xB7 zero-spend","Search tools","Deep Search, search providers and their router, a usage ledger, and a guard that blocks any search call that could cost money."],watchlist:["watchlist/","companies.json","The researched watchlist","About 130 companies in Hyderabad, Bengaluru and remote India, each with real AI work, early-career hiring, ratings and red flags."],storage:["storage.py","SQLite","Memory","A local SQLite database for jobs, documents, people, search runs and apply sessions \u2014 checked, repaired and backed up on every start."]},t=[["web"],["api"],["services"],["intelligence","discovery","generation","agents"],["config","tools","watchlist","storage"]],e=$t("#stack");e.innerHTML=t.map((i,r)=>(r?'<div class="join"></div>':"")+`<div class="lv" style="--n:${i.length}">${i.map(o=>`<button type="button" data-k="${o}" aria-pressed="false"><b>${s[o][0]}</b><span>${s[o][1]}</span></button>`).join("")}</div>`).join("");let n=i=>{on("button",e).forEach(r=>r.setAttribute("aria-pressed",r.dataset.k===i)),$t("#aiT").textContent=s[i][0],$t("#aiH").textContent=s[i][2],$t("#aiP").textContent=s[i][3],Ci||Le.from("#aiH, #aiP",{opacity:0,y:12,duration:.5,ease:"expo.out",stagger:.05})};e.addEventListener("click",i=>{let r=i.target.closest("button");r&&n(r.dataset.k)}),n("web")})();(()=>{let s=[["match","Why this score","Click a job and it opens beside the list.","Job list with an AI Engineer role scored 93 and its explanation"],["live_progress","Search, live","Real counts the server reports.","Search in progress with real counts"],["companies","Companies to watch","Verdicts, ratings and red flags.","Researched company watchlist"],["documents","Honest documents","Fact-checked, always one page.","Document editor with a one-page resume"],["browser","Auto-apply, live","The browser streams into the app.","Auto-apply with a live browser and step log"],["apply_help","When it needs you","Take over, then Continue.","Auto-apply waiting for the user"],["tracker","Track everything","One stage bar, one click onward.","Application tracker"],["dark","Dark mode","One click.","The app in dark mode"]],t=$t("#reel");t.innerHTML=s.map(([r,o,a,l],c)=>`<figure><button type="button" data-i="${c}" aria-label="Open full size: ${o}"><img src="assets/shots/${r}.webp" alt="${l}" loading="lazy" width="1440" height="900" draggable="false"></button><figcaption><b>${o}</b><span>${a}</span></figcaption></figure>`).join("");let e=$t("#zoom"),n=0;t.addEventListener("click",r=>{let o=r.target.closest("button");if(!o||n>6)return;let[a,l,c,h]=s[+o.dataset.i];$t("#zoomI").src=`assets/shots/${a}.webp`,$t("#zoomI").alt=h,$t("#zoomP").textContent=`${l} \u2014 ${c}`,e.showModal&&e.showModal()}),$t("#zoomX").addEventListener("click",()=>e.close()),e.addEventListener("click",r=>{r.target===e&&e.close()});let i=null;t.addEventListener("pointerdown",r=>{r.pointerType==="mouse"&&(i={x:r.clientX,s:t.scrollLeft},n=0)}),addEventListener("pointermove",r=>{i&&(n=Math.abs(r.clientX-i.x),n>6&&t.classList.add("drag"),t.scrollLeft=i.s-(r.clientX-i.x))}),addEventListener("pointerup",()=>{i=null,t.classList.remove("drag")})})();var ah=on("#osT button"),a0=ah.map(s=>document.getElementById(s.getAttribute("aria-controls"))),lh=["win","mac","lin"];function sp(s,t){let e=Math.max(0,lh.indexOf(s));ah.forEach((n,i)=>{n.setAttribute("aria-selected",i===e),n.tabIndex=i===e?0:-1,a0[i].hidden=i!==e}),Ci||Le.fromTo(a0[e],{opacity:0,y:20},{opacity:1,y:0,duration:.7,ease:"expo.out",overwrite:!0}),t&&ah[e].focus()}ah.forEach((s,t)=>{s.addEventListener("click",()=>sp(lh[t])),s.addEventListener("keydown",e=>{let n={ArrowDown:1,ArrowRight:1,ArrowUp:-1,ArrowLeft:-1}[e.key];n&&(e.preventDefault(),sp(lh[(t+n+3)%3],!0))})});oh[Gs]&&Gs!=="win"&&sp(Gs);(async()=>{try{let s=new AbortController;setTimeout(()=>s.abort(),6e3);let t=await fetch("https://api.github.com/repos/kvcops/JobHunterX/releases/latest",{signal:s.signal});if(!t.ok)return;let e=await t.json();(e.assets||[]).forEach(n=>on(`[data-sz="${CSS.escape(n.name)}"]`).forEach(i=>i.textContent=Math.round(n.size/1048576)+" MB")),e.name&&($t("#relLive").innerHTML=`Current: <a href="${e.html_url}">${e.name.replace(/^JobHunterX\s*/i,"v")}</a>.`)}catch{}})();var Hs=on("#seg button"),l0=$t("#seg i");function Ka(s,t){let e=Math.max(0,lh.indexOf(s));Hs.forEach((n,i)=>{n.setAttribute("aria-selected",i===e),n.tabIndex=i===e?0:-1}),l0.style.width=Hs[e].offsetWidth+"px",l0.style.transform=`translateX(${Hs[e].offsetLeft}px)`,on("#source [data-os]").forEach(n=>n.hidden=!n.dataset.os.split(" ").includes(s)),on("#source [data-pr]").forEach(n=>n.textContent=s==="win"?"PS> ":"$ "),t&&Hs[e].focus()}var f0=()=>(Hs.find(s=>s.getAttribute("aria-selected")==="true")||Hs[0]).dataset.o;Hs.forEach((s,t)=>{s.addEventListener("click",()=>{Ka(s.dataset.o),ie.refresh()}),s.addEventListener("keydown",e=>{let n={ArrowRight:1,ArrowLeft:-1}[e.key];n&&(e.preventDefault(),Ka(Hs[(t+n+3)%3].dataset.o,!0))})});Ka(oh[Gs]?Gs:"win");addEventListener("resize",()=>Ka(f0()));document.fonts&&document.fonts.ready.then(()=>Ka(f0()));var eT=async s=>{try{return await navigator.clipboard.writeText(s),!0}catch{let e=document.createElement("textarea");e.value=s,e.style.cssText="position:fixed;opacity:0",document.body.appendChild(e),e.select();let n=!1;try{n=document.execCommand("copy")}catch{}return e.remove(),n}};document.addEventListener("click",async s=>{let t=s.target.closest(".cp");if(!t)return;let e=await eT(t.dataset.c);t.textContent=e?"Copied":"Ctrl+C",t.classList.add("done"),np(e?"Copied":"Copy failed \u2014 select and copy"),clearTimeout(t._t),t._t=setTimeout(()=>{t.classList.remove("done"),t.textContent="Copy"},1600)});on(".more details").forEach(s=>s.addEventListener("toggle",()=>ie.refresh()));on(".qa details").forEach(s=>s.addEventListener("toggle",()=>ie.refresh()));})();
/*! Bundled license information:

gsap/gsap-core.js:
  (*!
   * GSAP 3.15.1
   * https://gsap.com
   *
   * @license Copyright 2008-2026, GreenSock. All rights reserved.
   * Subject to the terms at https://gsap.com/standard-license
   * @author: Jack Doyle, jack@greensock.com
  *)

gsap/CSSPlugin.js:
  (*!
   * CSSPlugin 3.15.1
   * https://gsap.com
   *
   * Copyright 2008-2026, GreenSock. All rights reserved.
   * Subject to the terms at https://gsap.com/standard-license
   * @author: Jack Doyle, jack@greensock.com
  *)

gsap/Observer.js:
  (*!
   * Observer 3.15.1
   * https://gsap.com
   *
   * @license Copyright 2008-2026, GreenSock. All rights reserved.
   * Subject to the terms at https://gsap.com/standard-license
   * @author: Jack Doyle, jack@greensock.com
  *)

gsap/ScrollTrigger.js:
  (*!
   * ScrollTrigger 3.15.1
   * https://gsap.com
   *
   * @license Copyright 2008-2026, GreenSock. All rights reserved.
   * Subject to the terms at https://gsap.com/standard-license
   * @author: Jack Doyle, jack@greensock.com
  *)

gsap/SplitText.js:
  (*!
   * SplitText 3.15.1
   * https://gsap.com
   *
   * @license Copyright 2008-2026, GreenSock. All rights reserved.
   * Subject to the terms at https://gsap.com/standard-license
   * @author: Jack Doyle
  *)

three/build/three.module.js:
  (**
   * @license
   * Copyright 2010-2024 Three.js Authors
   * SPDX-License-Identifier: MIT
   *)
*/
