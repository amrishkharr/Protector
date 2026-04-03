from flask import Flask, request, jsonify, render_template_string
from twilio.rest import Client
import urllib.request
import urllib.error
import json
import os

app = Flask(__name__)

# ============================================================
#  CONFIG — Add ALL of these in Render → Environment Variables
#
#   TWILIO_SID      →  get from twilio.com/console
#   TWILIO_AUTH     →  get from twilio.com/console
#   TWILIO_NUMBER   →  your Twilio phone number e.g. +18457738393
#   EMAIL_ADDRESS   →  nexus.srmist@gmail.com
#   BREVO_API_KEY   →  get from brevo.com → SMTP & API → API Keys
# ============================================================
TWILIO_SID    = os.environ.get("TWILIO_SID",    "ACb053c150e0efb5890ad3ff32c4686df8")
TWILIO_AUTH   = os.environ.get("TWILIO_AUTH",   "fb007c793be21d607121756b57d731b6")
TWILIO_NUMBER = os.environ.get("TWILIO_NUMBER", "+18457738393")
EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS", "nexus.srmist@gmail.com")
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")

try:
    twilio_client = Client(TWILIO_SID, TWILIO_AUTH) if TWILIO_SID and TWILIO_AUTH else None
except Exception:
    twilio_client = None

live_location = {}


# ============================================================
#  EMAIL via Brevo HTTP API — works on Render free tier
# ============================================================
def send_email_brevo(to_email, subject, html_body, plain_body):
    if not BREVO_API_KEY:
        raise Exception("BREVO_API_KEY not set in Render environment variables.")

    payload = json.dumps({
        "sender":      {"name": "Protractor SOS", "email": EMAIL_ADDRESS},
        "to":          [{"email": to_email}],
        "subject":     subject,
        "htmlContent": html_body,
        "textContent": plain_body,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=payload,
        headers={
            "api-key":      BREVO_API_KEY,
            "Content-Type": "application/json",
            "Accept":       "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status not in (200, 201):
                raise Exception(f"Brevo returned HTTP {resp.status}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        raise Exception(f"Brevo HTTP {e.code}: {body}")


# ============================================================
#  UI
# ============================================================
HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<title>Protractor</title>
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="theme-color" content="#0e0b1a">
<link rel="manifest" href="/manifest.json">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Sora:wght@700;800&display=swap" rel="stylesheet">
<script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
<link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css"/>
<style>
:root{
  --bg:#0e0b1a;--bg2:#130f22;--card:#17132a;--card2:#1e1935;
  --border:rgba(255,255,255,0.07);--border2:rgba(255,255,255,0.13);
  --text:#f0eeff;--sub:rgba(240,238,255,0.4);--sub2:rgba(240,238,255,0.22);
  --red:#ff4060;--red2:#ff7a5c;--redg:rgba(255,64,96,0.22);--redbg:rgba(255,64,96,0.08);
  --violet:#9b6dff;--violetg:rgba(155,109,255,0.15);
  --green:#3de8a0;--greeng:rgba(61,232,160,0.12);
  --amber:#ffb347;--r:20px;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{height:100%}
body{min-height:100%;font-family:'Plus Jakarta Sans',sans-serif;background:var(--bg);color:var(--text);overflow-x:hidden;-webkit-tap-highlight-color:transparent}
.bg-mesh{position:fixed;inset:0;pointer-events:none;z-index:0;
  background:
    radial-gradient(ellipse 600px 400px at 110% -10%,rgba(255,64,96,.07) 0%,transparent 60%),
    radial-gradient(ellipse 500px 500px at -10% 80%,rgba(155,109,255,.06) 0%,transparent 60%),
    radial-gradient(ellipse 300px 300px at 70% 55%,rgba(61,232,160,.04) 0%,transparent 60%)}
.wrap{position:relative;z-index:1;max-width:430px;margin:auto;padding-bottom:50px}
.header{padding:52px 20px 18px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:50;background:linear-gradient(to bottom,var(--bg) 75%,transparent)}
.hb{display:flex;align-items:center;gap:12px}
.logo{width:44px;height:44px;border-radius:15px;background:linear-gradient(135deg,var(--red),var(--red2));display:flex;align-items:center;justify-content:center;font-size:22px;box-shadow:0 0 28px var(--redg),0 4px 12px rgba(0,0,0,.5);flex-shrink:0}
.appname{font-family:'Sora',sans-serif;font-size:21px;font-weight:800;letter-spacing:-.5px;background:linear-gradient(90deg,#fff 0%,rgba(255,255,255,.55) 120%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.subline{font-size:10px;color:var(--sub);letter-spacing:1.2px;text-transform:uppercase;font-weight:500;margin-top:1px}
.live-badge{display:flex;align-items:center;gap:6px;background:var(--card);border:1px solid var(--border2);border-radius:30px;padding:8px 14px;font-size:11px;font-weight:700;color:var(--green);letter-spacing:.8px}
.ld{width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 10px var(--green);animation:ld 1.8s ease-in-out infinite}
@keyframes ld{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.25;transform:scale(.65)}}
.chips{display:flex;gap:8px;padding:0 14px;margin-bottom:8px}
.chip{flex:1;background:var(--card);border:1px solid var(--border);border-radius:16px;padding:10px 8px;display:flex;flex-direction:column;align-items:center;gap:3px}
.chip-ico{font-size:17px;line-height:1}
.chip-v{font-size:12px;font-weight:800;letter-spacing:.3px}
.chip-l{font-size:9px;color:var(--sub);letter-spacing:1.5px;text-transform:uppercase;font-weight:600}
.on{color:var(--green)}.wait{color:var(--amber)}.off{color:var(--sub)}
.sec{display:flex;align-items:center;gap:10px;padding:14px 18px 10px}
.sec-line{flex:1;height:1px;background:var(--border)}
.sec-txt{font-size:9px;font-weight:800;letter-spacing:2.5px;text-transform:uppercase;color:var(--sub);white-space:nowrap}
.card{margin:0 12px 12px;background:var(--card);border:1px solid var(--border);border-radius:var(--r);padding:18px;position:relative;overflow:hidden}
.card::after{content:'';position:absolute;inset:0;border-radius:inherit;background:linear-gradient(140deg,rgba(255,255,255,.025) 0%,transparent 55%);pointer-events:none}
.p-row{display:flex;align-items:center;gap:14px;margin-bottom:16px}
.p-av{width:50px;height:50px;border-radius:16px;flex-shrink:0;background:linear-gradient(135deg,rgba(155,109,255,.3),rgba(255,64,96,.15));border:1.5px solid rgba(155,109,255,.3);display:flex;align-items:center;justify-content:center;font-family:'Sora',sans-serif;font-size:20px;font-weight:800;color:var(--violet)}
.p-lbl{font-size:10px;color:var(--sub);letter-spacing:1px;text-transform:uppercase;font-weight:600}
.p-name{font-size:16px;font-weight:700;margin-top:1px}
.field{position:relative;margin-bottom:10px}
.field-lbl{font-size:10px;color:var(--sub);letter-spacing:1px;text-transform:uppercase;font-weight:700;margin-bottom:5px;padding-left:1px}
.field input{width:100%;background:var(--bg2);border:1.5px solid var(--border);border-radius:13px;padding:13px 14px 13px 40px;color:var(--text);font-family:'Plus Jakarta Sans',sans-serif;font-size:14px;font-weight:500;outline:none;-webkit-appearance:none;transition:border-color .2s,box-shadow .2s}
.field input::placeholder{color:var(--sub2)}
.field input:focus{border-color:rgba(155,109,255,.5);box-shadow:0 0 0 3px rgba(155,109,255,.08)}
.fi{position:absolute;left:13px;bottom:14px;font-size:14px;pointer-events:none;opacity:.7}
.btn-save{width:100%;margin-top:4px;background:linear-gradient(135deg,rgba(155,109,255,.18),rgba(155,109,255,.08));border:1.5px solid rgba(155,109,255,.3);border-radius:13px;color:var(--violet);font-family:'Plus Jakarta Sans',sans-serif;font-weight:700;font-size:13px;padding:13px;cursor:pointer;letter-spacing:.4px;display:flex;align-items:center;justify-content:center;gap:7px;transition:background .15s,transform .1s}
.btn-save:active{transform:scale(.98)}
.contacts-hd{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}
.contacts-title{font-size:15px;font-weight:800}
.contacts-badge{font-size:11px;font-weight:700;letter-spacing:.5px;background:var(--violetg);border:1px solid rgba(155,109,255,.25);color:var(--violet);border-radius:20px;padding:3px 10px}
#contact-list{display:flex;flex-direction:column;gap:10px;margin-bottom:14px}
.no-c{text-align:center;padding:22px 0 6px;color:var(--sub);font-size:13px;font-weight:500;line-height:1.9}
.no-c-ico{font-size:30px;display:block;margin-bottom:8px;opacity:.55}
.c-item{display:flex;align-items:stretch;background:var(--card2);border:1.5px solid var(--border);border-radius:16px;overflow:hidden;animation:ci .25s ease;transition:border-color .2s,transform .1s}
.c-item:active{transform:scale(.99)}
@keyframes ci{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
.c-accent{width:4px;flex-shrink:0}
.c-av{width:42px;height:42px;border-radius:12px;flex-shrink:0;margin:13px 0 13px 12px;display:flex;align-items:center;justify-content:center;font-family:'Sora',sans-serif;font-size:18px;font-weight:800;border:1.5px solid}
.c-body{flex:1;padding:12px 10px;min-width:0}
.c-name{font-size:14px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:6px}
.c-pills{display:flex;flex-wrap:wrap;gap:5px}
.c-pill{display:flex;align-items:center;gap:4px;background:var(--bg2);border:1px solid var(--border);border-radius:8px;padding:3px 8px;font-size:10px;font-weight:600;color:var(--sub);max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.c-del{width:54px;flex-shrink:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;background:transparent;border:none;border-left:1px solid var(--border);cursor:pointer;color:var(--sub2);font-size:14px;transition:background .15s,color .15s;-webkit-tap-highlight-color:transparent}
.c-del-lbl{font-size:8px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;color:inherit}
.c-del:active{background:rgba(255,64,96,.12);color:var(--red)}
.btn-add{width:100%;display:flex;align-items:center;justify-content:center;gap:8px;background:var(--redbg);border:1.5px dashed rgba(255,64,96,.35);border-radius:14px;padding:13px;color:var(--red);font-family:'Plus Jakarta Sans',sans-serif;font-weight:700;font-size:13px;letter-spacing:.3px;cursor:pointer;transition:background .15s,transform .1s}
.btn-add:active{transform:scale(.98);background:rgba(255,64,96,.14)}
.sos-wrap{margin:0 12px 12px;background:var(--card);border:1.5px solid rgba(255,64,96,.2);border-radius:26px;padding:26px 18px 22px;position:relative;overflow:hidden;text-align:center}
.sos-wrap::before{content:'';position:absolute;top:0;left:50%;transform:translateX(-50%);width:180px;height:1px;background:linear-gradient(90deg,transparent,rgba(255,64,96,.7),transparent)}
.sos-eyebrow{font-size:9px;font-weight:800;letter-spacing:3.5px;text-transform:uppercase;color:rgba(255,64,96,.6);margin-bottom:20px}
.sos-btn{width:136px;height:136px;border-radius:50%;border:none;background:none;padding:0;cursor:pointer;position:relative;display:inline-block;margin-bottom:18px;-webkit-tap-highlight-color:transparent}
.sr{position:absolute;border-radius:50%;animation:sr 2.8s ease-out infinite}
.sr1{inset:0;border:1.5px solid rgba(255,64,96,.3);animation-delay:0s}
.sr2{inset:-15px;border:1.5px solid rgba(255,64,96,.18);animation-delay:.7s}
.sr3{inset:-30px;border:1.5px solid rgba(255,64,96,.1);animation-delay:1.4s}
@keyframes sr{0%{opacity:.9;transform:scale(.88)}100%{opacity:0;transform:scale(1.12)}}
.sos-core{position:relative;z-index:2;width:100%;height:100%;border-radius:50%;background:linear-gradient(145deg,#ff2a4e,#e01035);display:flex;flex-direction:column;align-items:center;justify-content:center;box-shadow:0 0 0 6px rgba(255,40,78,.15),0 0 48px rgba(255,40,78,.45),inset 0 2px 6px rgba(255,255,255,.18),0 6px 28px rgba(0,0,0,.5);transition:transform .12s,box-shadow .12s}
.sos-btn:active .sos-core{transform:scale(.92);box-shadow:0 0 0 6px rgba(255,40,78,.25),0 0 24px rgba(255,40,78,.55)}
.sos-ico{font-size:36px;line-height:1;filter:drop-shadow(0 2px 6px rgba(0,0,0,.4))}
.sos-lbl{font-family:'Sora',sans-serif;font-weight:800;font-size:13px;letter-spacing:3.5px;color:white;margin-top:5px}
.sos-footer{display:flex;align-items:center;justify-content:center;gap:10px;flex-wrap:wrap}
.sos-desc{font-size:12px;color:var(--sub);line-height:1.7}
.sos-desc b{color:rgba(255,120,100,.85);font-weight:600}
.sos-stat{display:flex;align-items:center;gap:6px;background:rgba(61,232,160,.08);border:1px solid rgba(61,232,160,.2);border-radius:20px;padding:5px 12px;font-size:11px;font-weight:700;color:var(--green)}
.map-bar{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}
.map-title{font-size:15px;font-weight:700}
.map-pill{display:flex;align-items:center;gap:5px;background:var(--greeng);border:1px solid rgba(61,232,160,.2);border-radius:20px;padding:5px 12px;font-size:10px;font-weight:700;color:var(--green);letter-spacing:.5px}
#map{height:220px;border-radius:15px;overflow:hidden;border:1px solid var(--border)}
.leaflet-tile{filter:brightness(.55) saturate(.45) hue-rotate(210deg)}
.leaflet-control-attribution{display:none!important}
.backdrop{position:fixed;inset:0;background:rgba(8,6,18,.82);backdrop-filter:blur(10px);z-index:200;display:none;align-items:flex-end;justify-content:center}
.backdrop.open{display:flex}
.sheet{background:var(--card);border:1px solid var(--border2);border-radius:28px 28px 0 0;padding:20px 18px 48px;width:100%;max-width:430px;animation:sh .3s cubic-bezier(.22,1,.36,1)}
@keyframes sh{from{transform:translateY(100%);opacity:0}to{transform:translateY(0);opacity:1}}
.sh-handle{width:36px;height:4px;background:var(--border2);border-radius:2px;margin:0 auto 20px}
.sh-head{font-family:'Sora',sans-serif;font-size:20px;font-weight:800;margin-bottom:20px}
.sh-actions{display:flex;gap:10px;margin-top:16px}
.btn-cancel{flex:1;padding:13px;border-radius:13px;border:1.5px solid var(--border2);background:var(--card2);color:var(--sub);font-family:'Plus Jakarta Sans',sans-serif;font-weight:700;font-size:14px;cursor:pointer}
.btn-confirm{flex:2;padding:13px;border-radius:13px;border:none;background:linear-gradient(135deg,var(--red),var(--red2));color:white;font-family:'Plus Jakarta Sans',sans-serif;font-weight:800;font-size:14px;cursor:pointer;box-shadow:0 4px 20px var(--redg);transition:transform .1s}
.btn-confirm:active{transform:scale(.97)}
.toast{position:fixed;bottom:28px;left:50%;transform:translateX(-50%);background:rgba(14,11,26,.97);backdrop-filter:blur(20px);border:1px solid var(--border2);border-radius:14px;padding:12px 22px;font-size:13px;font-weight:600;white-space:nowrap;display:none;z-index:999;box-shadow:0 8px 36px rgba(0,0,0,.55);animation:tin .22s ease forwards}
@keyframes tin{from{opacity:0;transform:translateX(-50%) translateY(14px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}
@supports(padding-bottom:env(safe-area-inset-bottom)){.wrap{padding-bottom:calc(50px + env(safe-area-inset-bottom))}.sheet{padding-bottom:calc(44px + env(safe-area-inset-bottom))}}
</style>
<script>if("serviceWorker"in navigator)navigator.serviceWorker.register("/static/sw.js");</script>
</head>
<body>
<div class="bg-mesh"></div>
<div class="wrap">

  <div class="header">
    <div class="hb">
      <div class="logo">🔐</div>
      <div>
        <div class="appname">Protractor</div>
        <div class="subline">Personal Safety Guard</div>
      </div>
    </div>
    <div class="live-badge"><div class="ld"></div>LIVE</div>
  </div>

  <div class="chips">
    <div class="chip"><div class="chip-ico">🛰️</div><div class="chip-v on" id="gps-status">ON</div><div class="chip-l">GPS</div></div>
    <div class="chip"><div class="chip-ico">🎙️</div><div class="chip-v wait" id="voice-status">WAIT</div><div class="chip-l">Voice</div></div>
    <div class="chip"><div class="chip-ico">👥</div><div class="chip-v on" id="cc-chip">0</div><div class="chip-l">Contacts</div></div>
    <div class="chip"><div class="chip-ico">🚀</div><div class="chip-v on">READY</div><div class="chip-l">Alert</div></div>
  </div>

  <div class="sec"><div class="sec-line"></div><div class="sec-txt">Your Profile</div><div class="sec-line"></div></div>
  <div class="card">
    <div class="p-row">
      <div class="p-av" id="p-av">?</div>
      <div><div class="p-lbl">Signed in as</div><div class="p-name" id="username">User</div></div>
    </div>
    <div class="field">
      <div class="field-lbl">Your Name</div>
      <span class="fi">👤</span>
      <input id="name" type="text" placeholder="Enter your full name" autocomplete="name">
    </div>
    <button class="btn-save" onclick="save()">💾&nbsp; Save Profile</button>
  </div>

  <div class="sec"><div class="sec-line"></div><div class="sec-txt">Emergency Contacts</div><div class="sec-line"></div></div>
  <div class="card">
    <div class="contacts-hd">
      <div class="contacts-title">Who to Alert</div>
      <div class="contacts-badge" id="c-badge">0 contacts</div>
    </div>
    <div id="contact-list"></div>
    <button class="btn-add" onclick="openModal()">＋&nbsp; Add Emergency Contact</button>
  </div>

  <div class="sec"><div class="sec-line"></div><div class="sec-txt">Emergency Alert</div><div class="sec-line"></div></div>
  <div class="sos-wrap">
    <div class="sos-eyebrow">Panic Button — Alerts All Contacts Instantly</div>
    <button class="sos-btn" onclick="sendSOS()" aria-label="SOS">
      <div class="sr sr1"></div><div class="sr sr2"></div><div class="sr sr3"></div>
      <div class="sos-core"><div class="sos-ico">🚨</div><div class="sos-lbl">SOS</div></div>
    </button>
    <div class="sos-footer">
      <div class="sos-desc">Sends <b>SMS + Email</b> with live GPS<br>to every contact above</div>
      <div class="sos-stat">🛡️ <span id="sos-count">0</span> contacts ready</div>
    </div>
  </div>

  <div class="sec"><div class="sec-line"></div><div class="sec-txt">Live Location</div><div class="sec-line"></div></div>
  <div class="card">
    <div class="map-bar">
      <div class="map-title">Tracking Now</div>
      <div class="map-pill">● LIVE</div>
    </div>
    <div id="map"></div>
  </div>

</div>

<!-- ADD CONTACT MODAL -->
<div class="backdrop" id="modal" onclick="closeOnBackdrop(event)">
  <div class="sheet">
    <div class="sh-handle"></div>
    <div class="sh-head">New Contact</div>
    <div class="field">
      <div class="field-lbl">Name / Label</div>
      <span class="fi">🏷️</span>
      <input id="m-name" type="text" placeholder="e.g. Mom, Dad, Brother">
    </div>
    <div class="field">
      <div class="field-lbl">Phone Number</div>
      <span class="fi">📞</span>
      <input id="m-phone" type="tel" placeholder="+91 XXXXX XXXXX">
    </div>
    <div class="field">
      <div class="field-lbl">Email Address</div>
      <span class="fi">✉️</span>
      <input id="m-email" type="email" placeholder="email@example.com">
    </div>
    <div class="sh-actions">
      <button class="btn-cancel" onclick="closeModal()">Cancel</button>
      <button class="btn-confirm" onclick="addContact()">Add Contact</button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
const map=L.map('map',{zoomControl:false,attributionControl:false}).setView([20.5937,78.9629],13);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
const pin=L.divIcon({className:'',html:'<div style="width:18px;height:18px;border-radius:50%;background:linear-gradient(135deg,#ff4060,#ff7a5c);border:3px solid #fff;box-shadow:0 0 0 3px rgba(255,64,96,.4),0 3px 12px rgba(0,0,0,.6)"></div>',iconSize:[18,18],iconAnchor:[9,9]});
const marker=L.marker([0,0],{icon:pin}).addTo(map);

function toast(msg){const t=document.getElementById('toast');t.textContent=msg;t.style.display='block';clearTimeout(t._t);t._t=setTimeout(()=>t.style.display='none',3200)}

function save(){
  const n=document.getElementById('name').value.trim();
  if(!n){toast('Enter your name first');return}
  document.cookie='username='+encodeURIComponent(n)+'; path=/; max-age=31536000';
  document.getElementById('username').textContent=n;
  document.getElementById('p-av').textContent=n.charAt(0).toUpperCase();
  toast('✅ Profile saved');
}
function getCookie(k){const v=document.cookie.match('(^|;) ?'+k+'=([^;]*)(;|$)');return v?decodeURIComponent(v[2]):null}
(function(){const n=getCookie('username')||'';if(n){document.getElementById('username').textContent=n;document.getElementById('name').value=n;document.getElementById('p-av').textContent=n.charAt(0).toUpperCase()}})();

let contacts=[];
const PALETTE=[
  {bg:'rgba(255,64,96,.18)',border:'rgba(255,64,96,.3)',txt:'#ff4060',strip:'linear-gradient(to bottom,#ff4060,#ff7a5c)'},
  {bg:'rgba(155,109,255,.18)',border:'rgba(155,109,255,.3)',txt:'#9b6dff',strip:'linear-gradient(to bottom,#9b6dff,#c084fc)'},
  {bg:'rgba(61,232,160,.15)',border:'rgba(61,232,160,.3)',txt:'#3de8a0',strip:'linear-gradient(to bottom,#3de8a0,#22d3ee)'},
  {bg:'rgba(255,179,71,.15)',border:'rgba(255,179,71,.3)',txt:'#ffb347',strip:'linear-gradient(to bottom,#ffb347,#ffd700)'},
  {bg:'rgba(91,200,255,.15)',border:'rgba(91,200,255,.3)',txt:'#5bc8ff',strip:'linear-gradient(to bottom,#5bc8ff,#3b82f6)'},
];
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
function loadContacts(){try{contacts=JSON.parse(localStorage.getItem('protractor_contacts')||'[]')}catch{contacts=[]}renderContacts()}
function saveContacts(){localStorage.setItem('protractor_contacts',JSON.stringify(contacts))}
function renderContacts(){
  const n=contacts.length;
  document.getElementById('c-badge').textContent=n+' contact'+(n!==1?'s':'');
  document.getElementById('cc-chip').textContent=n;
  document.getElementById('sos-count').textContent=n;
  const list=document.getElementById('contact-list');
  if(!n){list.innerHTML='<div class="no-c"><span class="no-c-ico">🤝</span>No contacts added yet.<br>Add people who should be<br>alerted in an emergency.</div>';return}
  list.innerHTML=contacts.map((c,i)=>{
    const p=PALETTE[i%PALETTE.length];
    const init=(c.name||'?').charAt(0).toUpperCase();
    const ph=c.phone?`<div class="c-pill"><span>📞</span>${esc(c.phone)}</div>`:'';
    const em=c.email?`<div class="c-pill"><span>✉️</span>${esc(c.email)}</div>`:'';
    return `<div class="c-item">
      <div class="c-accent" style="background:${p.strip}"></div>
      <div class="c-av" style="background:${p.bg};border-color:${p.border};color:${p.txt}">${init}</div>
      <div class="c-body"><div class="c-name">${esc(c.name)}</div><div class="c-pills">${ph}${em}</div></div>
      <button class="c-del" onclick="removeContact(${i})" aria-label="Remove"><span>✕</span><span class="c-del-lbl">Remove</span></button>
    </div>`;
  }).join('');
}
function removeContact(i){const nm=contacts[i].name;contacts.splice(i,1);saveContacts();renderContacts();toast('🗑 '+nm+' removed')}
function openModal(){document.getElementById('modal').classList.add('open');setTimeout(()=>document.getElementById('m-name').focus(),340)}
function closeModal(){document.getElementById('modal').classList.remove('open');['m-name','m-phone','m-email'].forEach(id=>document.getElementById(id).value='')}
function closeOnBackdrop(e){if(e.target===document.getElementById('modal'))closeModal()}
function addContact(){
  const n=document.getElementById('m-name').value.trim();
  const p=document.getElementById('m-phone').value.trim();
  const e=document.getElementById('m-email').value.trim();
  if(!n){toast('Enter a name');return}
  if(!p&&!e){toast('Add phone or email');return}
  contacts.push({name:n,phone:p,email:e});saveContacts();renderContacts();closeModal();toast('✓ '+n+' added');
}

navigator.geolocation.watchPosition(pos=>{
  fetch('/update_location',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({lat:pos.coords.latitude,lng:pos.coords.longitude})});
  marker.setLatLng([pos.coords.latitude,pos.coords.longitude]);map.setView([pos.coords.latitude,pos.coords.longitude],15);
  const s=document.getElementById('gps-status');s.textContent='ON';s.className='chip-v on';
},()=>{toast('Enable GPS for tracking');const s=document.getElementById('gps-status');s.textContent='OFF';s.className='chip-v off'},{enableHighAccuracy:true});

function sendSOS(){
  if(!contacts.length){toast('⚠️ Add a contact first');return}
  const uname=document.getElementById('name').value.trim()||getCookie('username')||'Unknown';
  if(uname==='Unknown'){toast('⚠️ Please save your name first');return}
  toast('🚨 Sending SOS to '+contacts.length+' contact'+(contacts.length>1?'s':'')+'...');
  let done=0,ok=0,fail=0;
  contacts.forEach(c=>{
    fetch('/sos',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({name:uname,phone:c.phone||'',email:c.email||''})
    })
    .then(r=>r.json())
    .then(d=>{
      done++;
      if(d.status&&d.status.includes('✅')){ok++}
      else{fail++;console.error(c.name+':',d.status,d.trace||'');toast('❌ '+c.name+': '+(d.status||'Unknown error'))}
      if(done===contacts.length){
        if(ok>0&&fail===0)toast('✅ SOS sent to all '+ok+' contact'+(ok>1?'s':'')+'!');
        else if(ok>0)toast('⚠️ Sent to '+ok+', failed '+fail);
        else toast('❌ All sends failed. Check Render logs.');
      }
    })
    .catch(err=>{done++;fail++;toast('❌ Network error: '+err.message)});
  });
}

const keywords=["help","save me","stop","danger"];
function autoCall(){const f=contacts.find(c=>c.phone);if(f)window.location.href='tel:'+f.phone}
function triggerAutoSOS(){toast('Keyword detected! SOS firing...');sendSOS();autoCall()}
function startVoice(){
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR){const v=document.getElementById('voice-status');v.textContent='N/A';v.className='chip-v off';return}
  const r=new SR();r.continuous=true;r.lang='en-US';r.interimResults=false;
  r.onresult=e=>{const txt=e.results[e.results.length-1][0].transcript.toLowerCase();for(const k of keywords)if(txt.includes(k)){triggerAutoSOS();break}};
  r.onerror=()=>{};r.onend=()=>r.start();r.start();
  const v=document.getElementById('voice-status');v.textContent='ON';v.className='chip-v on';
}
loadContacts();
setTimeout(startVoice,2000);
</script>
</body>
</html>"""


# ============================================================
#  ROUTES
# ============================================================
@app.route("/")
def home():
    return render_template_string(HTML)


@app.route("/update_location", methods=["POST"])
def update_location():
    data = request.json
    live_location["lat"] = data.get("lat")
    live_location["lng"] = data.get("lng")
    return jsonify({"status": "updated"})


@app.route("/sos", methods=["POST"])
def sos():
    try:
        data = request.json
        lat  = live_location.get("lat")
        lng  = live_location.get("lng")

        if not lat or not lng:
            return jsonify({"status": "❌ Location not available yet. Allow GPS and wait a few seconds, then try again."})

        map_url = f"https://www.google.com/maps?q={lat},{lng}"
        errors  = []

        # ── SMS via Twilio ──────────────────────────────────────────
        if data.get("phone"):
            try:
                if not twilio_client:
                    raise Exception("Twilio not set up. Add TWILIO_SID, TWILIO_AUTH, TWILIO_NUMBER in Render env vars.")
                sms_body = (
                    f"🚨 SOS ALERT — PROTRACTOR\n"
                    f"{'─'*24}\n"
                    f"👤 Person : {data['name']}\n"
                    f"📍 Coords : {lat:.5f}, {lng:.5f}\n"
                    f"🗺  Maps  : {map_url}\n"
                    f"{'─'*24}\n"
                    f"⚠️ Needs IMMEDIATE help.\n"
                    f"📞 Call them or dial 112 now."
                )
                twilio_client.messages.create(
                    body=sms_body,
                    from_=TWILIO_NUMBER,
                    to=data["phone"]
                )
            except Exception as e:
                errors.append(f"SMS: {e}")

        # ── Email via Brevo HTTP API ────────────────────────────────
        if data.get("email"):
            try:
                html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>SOS Alert</title></head>
<body style="margin:0;padding:0;background:#f0ebe2;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f0ebe2;padding:32px 0;">
    <tr><td align="center">
      <table width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:520px;">
        <tr><td style="height:5px;background:#c8392b;border-radius:8px 8px 0 0;"></td></tr>
        <tr><td style="background:#1a1612;padding:28px 32px 22px;">
          <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
            <td>
              <div style="font-size:22px;font-weight:900;color:#f5f0e8;">Protractor<span style="color:#c8392b;">.</span></div>
              <div style="font-size:10px;letter-spacing:3px;text-transform:uppercase;color:#8a8070;margin-top:3px;">Personal Safety Guard</div>
            </td>
            <td align="right"><div style="background:#c8392b;border-radius:50%;width:44px;height:44px;text-align:center;line-height:44px;font-size:22px;">&#128737;</div></td>
          </tr></table>
        </td></tr>
        <tr><td style="background:#c8392b;padding:20px 32px;">
          <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
            <td>
              <div style="font-size:11px;letter-spacing:3px;text-transform:uppercase;color:rgba(255,255,255,.65);margin-bottom:6px;">Emergency Alert</div>
              <div style="font-size:26px;font-weight:900;color:#fff;line-height:1.1;">&#128680; SOS Triggered</div>
            </td>
            <td align="right" style="vertical-align:top;">
              <div style="background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.25);border-radius:20px;padding:5px 12px;font-size:11px;font-weight:600;color:white;white-space:nowrap;">URGENT</div>
            </td>
          </tr></table>
        </td></tr>
        <tr><td style="background:#ffffff;padding:28px 32px;">
          <p style="margin:0 0 20px;font-size:14px;color:#5a5248;line-height:1.7;">
            <strong style="color:#1a1612;">{data['name']}</strong> has triggered an emergency SOS alert via Protractor. Please respond immediately or contact emergency services.
          </p>
          <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:16px;">
            <tr><td style="padding-bottom:10px;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#fdecea;border:1px solid #f0c4bf;border-radius:12px;padding:14px 16px;"><tr>
                <td style="font-size:18px;width:36px;vertical-align:middle;">&#128100;</td>
                <td style="padding-left:10px;vertical-align:middle;">
                  <div style="font-size:10px;letter-spacing:1.5px;text-transform:uppercase;color:#c8392b;font-weight:600;">Person in distress</div>
                  <div style="font-size:15px;font-weight:700;color:#1a1612;margin-top:2px;">{data['name']}</div>
                </td>
              </tr></table>
            </td></tr>
            <tr><td>
              <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f5f0e8;border:1px solid #e0d8cc;border-radius:12px;padding:14px 16px;"><tr>
                <td style="font-size:18px;width:36px;vertical-align:middle;">&#128205;</td>
                <td style="padding-left:10px;vertical-align:middle;">
                  <div style="font-size:10px;letter-spacing:1.5px;text-transform:uppercase;color:#8a8070;font-weight:600;">GPS Coordinates</div>
                  <div style="font-size:13px;font-weight:600;color:#1a1612;margin-top:2px;font-family:monospace;">{lat:.6f}, {lng:.6f}</div>
                </td>
              </tr></table>
            </td></tr>
          </table>
          <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:24px;">
            <tr><td align="center">
              <a href="{map_url}" target="_blank" style="display:inline-block;background:#c8392b;color:#fff;text-decoration:none;font-size:14px;font-weight:700;padding:14px 32px;border-radius:12px;">
                &#128205;&nbsp; Open Live Location on Maps
              </a>
            </td></tr>
          </table>
          <hr style="border:none;border-top:1px solid #ece6d9;margin:0 0 16px;">
          <div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#8a8070;font-weight:600;margin-bottom:10px;">Recommended Actions</div>
          <table width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr><td style="padding-bottom:8px;font-size:13px;color:#2e2820;line-height:1.5;">&#128222; Call <strong>{data['name']}</strong> immediately to check their status</td></tr>
            <tr><td style="padding-bottom:8px;font-size:13px;color:#2e2820;line-height:1.5;">&#128506; Use the location link above to find their exact position</td></tr>
            <tr><td style="font-size:13px;color:#2e2820;line-height:1.5;">&#128659; Contact emergency services (112) if unreachable</td></tr>
          </table>
        </td></tr>
        <tr><td style="background:#1a1612;padding:18px 32px;border-radius:0 0 8px 8px;">
          <div style="font-size:12px;color:#8a8070;">Sent by <strong style="color:#f5f0e8;">Protractor</strong> safety app &nbsp;|&nbsp; Automated alert — do not ignore.</div>
        </td></tr>
        <tr><td style="height:4px;background:#c8392b;border-radius:0 0 8px 8px;"></td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""
                plain_body = (
                    f"SOS ALERT from Protractor!\n"
                    f"Person: {data['name']}\n"
                    f"Location: {map_url}\n"
                    f"Coords: {lat:.6f}, {lng:.6f}\n\n"
                    f"This person needs immediate help. Call them or dial 112."
                )
                subject = f"🚨 SOS Alert — {data['name']} needs help NOW"
                send_email_brevo(data["email"], subject, html_body, plain_body)
            except Exception as e:
                errors.append(f"Email: {e}")

        if errors:
            return jsonify({"status": f"❌ Error: {'; '.join(errors)}"})
        return jsonify({"status": "✅ SOS sent successfully!"})

    except Exception as e:
        import traceback
        return jsonify({"status": f"❌ Server error: {str(e)}", "trace": traceback.format_exc()})


@app.route("/manifest.json")
def manifest():
    return jsonify({
        "name": "Protractor", "short_name": "Protractor",
        "start_url": "/", "display": "standalone",
        "background_color": "#0e0b1a", "theme_color": "#ff4060",
        "icons": [
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"}
        ]
    })


# ============================================================
#  START
# ============================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
