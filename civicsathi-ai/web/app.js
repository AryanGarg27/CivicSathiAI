"use strict";
const $ = id => document.getElementById(id);
const categories={grievance:"Public grievance",property_tax:"Property tax",echallan:"E-challans",horticulture:"Horticulture",license:"Licences and renewals",water_sewage:"Water and sewerage",health:"Health & medical",social_welfare:"Social welfare",centres:"Sampark centres",other:"Unclear / other"};
const statuses={received:"Received",under_review:"Under review",in_progress:"In progress",resolved:"Resolved",rejected:"Rejected"};
let me=null, services=[], photoId=null, photoData="", currentDraft=null, requestId=crypto.randomUUID(), busy=false;
function node(tag, content, cls){const e=document.createElement(tag);if(content!==undefined)e.textContent=content;if(cls)e.className=cls;return e;}
async function api(url,options={}) {
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),65000);
 try{const r=await fetch(url,{...options,credentials:"same-origin",signal:controller.signal,headers:{"Content-Type":"application/json",...(options.headers||{})}});
 const data=await r.json();if(!r.ok){const msg=typeof data.detail==="string"?data.detail:Array.isArray(data.detail)?data.detail.map(x=>x.msg).join("; "):"Request failed";throw new Error(msg);}return data;
 }catch(e){if(e.name==="AbortError")throw new Error("Request timed out. Please try again.");throw e;}finally{clearTimeout(timer);}
}
const post=(url,body)=>api(url,{method:"POST",body:JSON.stringify(body)});
function goSignIn(){location.href="/sign-in?next="+encodeURIComponent(location.pathname);}
async function bootstrap(){
 try{const h=await api("/api/health");const s=$("systemStatus");if(s){s.hidden=false;s.textContent="Connected · Google AI "+(h.google_configured?"ready":"needs configuration")+" · Private account storage";s.classList.toggle("ready",h.google_configured);}
 const result=await api("/api/auth/me");me=result.user;
 const account=$("accountLink");if(account){account.href=me?"/account":"/sign-in";account.textContent=me?"My account":"Sign in";}
 const profileLink=$("profileLink");if(profileLink)profileLink.hidden=!me;
 const staff=$("staffLink");if(staff&&me?.role==="staff")staff.hidden=false;
 if(["/report","/ask","/track","/account","/profile","/staff"].includes(location.pathname)&&!me){goSignIn();return;}
 if(location.pathname==="/staff"&&me?.role!=="staff"){location.href="/";return;}
 initPage();
 }catch(e){const s=$("systemStatus");if(s){s.hidden=false;s.textContent="App server is unavailable. Refresh after it starts.";}}
}
function initPage(){
 if($("authForm"))initAuth();
 if($("profileForm"))initProfile();
 if($("services"))loadServices();
 if($("serviceRequestForm"))initServiceRequest();
 if($("askForm"))initAsk();
 if($("locateCentre"))initEasyHelp();
 if($("analyze"))initReport();
 if($("myCases"))loadMyCases();
 if($("myRequests"))loadMyRequests();
 if($("accountCases"))initAccount();
 if($("staffCases"))initStaff();
}
function initAsk(){
 let currentDraft=null,requestKey=crypto.randomUUID();
 $("askForm").addEventListener("submit",async event=>{event.preventDefault();const text=$("requestText").value.trim();if(text.length<5){$("askNotice").textContent="Please add a little more detail.";return;}
  const button=$("understandRequest");button.disabled=true;$("askNotice").textContent="Understanding your request…";$("aiResult").hidden=true;
  try{const result=await post("/api/intake",{text});currentDraft=result.draft;currentDraft.source_text=text;requestKey=crypto.randomUUID();const service=result.service;
   $("suggestedService").textContent=service?.name||"I need one more detail";$("suggestedDescription").textContent=service?.description||"Try adding what you need and where, in your own words.";
   $("aiMode").textContent=result.mode==="safe-fallback"?"AI service unavailable · showing a basic suggestion. Please check carefully.":"Suggested category: "+(categories[currentDraft.category]||currentDraft.category)+". Please check before saving.";
   $("requestSummary").value=currentDraft.summary;$("requestLocation").value=currentDraft.location||"";
   const container=$("matchedDetails");container.replaceChildren();if(service?.source){const link=node("a","Official service information ↗");link.href=service.source;link.target="_blank";link.rel="noopener noreferrer";container.append(link);}else container.textContent="No service match yet; please add detail and try again.";
   $("saveRequest").hidden=currentDraft.category==="other";$("confirmRequest").checked=false;$("aiResult").hidden=false;
   if(currentDraft.category!=="other"){
    sessionStorage.setItem("civicsathi-intake-draft",JSON.stringify(currentDraft));
    const target=["health","social_welfare","horticulture"].includes(currentDraft.category)
      ?"/apply?service="+encodeURIComponent(currentDraft.service_type||({health:"health_appointment",social_welfare:"social_welfare",horticulture:"horticulture"})[currentDraft.category])
      :"/report";
    $("askNotice").textContent="Request understood. Opening the matching form with the details you provided…";
    location.href=target;return;
   }
   $("askNotice").textContent="I need a little more detail before routing this request. Add context and try again.";
  }catch(error){$("askNotice").textContent=error.message;}finally{button.disabled=false;}
 });
 $("saveRequest").addEventListener("click",async()=>{if(!currentDraft)return;if(!$("confirmRequest").checked){$("saveNotice").textContent="Please confirm that you reviewed the request.";return;}
  const draft={...currentDraft,summary:$("requestSummary").value.trim(),location:$("requestLocation").value.trim()||null};if(!draft.summary){$("saveNotice").textContent="Add a short summary before saving.";return;}
  const save=$("saveRequest");save.disabled=true;try{const item=await post("/api/cases",{draft,confirmed:true,request_id:requestKey});$("saveNotice").textContent="Saved to your account. Tracking number: "+item.id+". You can check its progress on Nearby help or Track.";save.hidden=true;}catch(error){$("saveNotice").textContent=error.message;}finally{save.disabled=false;}
 });
 initVoiceInput("voiceInput","requestText","voiceLanguage","voiceNotice");
}
function initVoiceInput(buttonId,textId,languageId,noticeId){
 const voice=$(buttonId);voice?.addEventListener("click",()=>{
  const Recognizer=window.SpeechRecognition||window.webkitSpeechRecognition,notice=$(noticeId);
  if(!Recognizer){notice.textContent="This browser does not provide voice typing. Try Chrome or Edge, allow microphone access, or use the microphone on your device keyboard.";return;}
  if(!window.isSecureContext){notice.textContent="Voice typing needs a secure page (HTTPS or localhost). Open the app using localhost or its HTTPS address.";return;}
  const recog=new Recognizer();recog.lang=$(languageId).value;recog.interimResults=false;recog.continuous=false;
  voice.disabled=true;notice.textContent="Starting microphone…";
  recog.onstart=()=>{notice.textContent="Listening… speak now.";};
  recog.onresult=e=>{const transcript=e.results?.[0]?.[0]?.transcript;if(transcript){const input=$(textId);input.value=(input.value+" "+transcript).trim();input.dispatchEvent(new Event("input",{bubbles:true}));notice.textContent="Voice input added. Review your words before continuing.";}else notice.textContent="No words were recognized. Try again or type your request.";};
  recog.onerror=e=>{const messages={"not-allowed":"Microphone access is blocked. Allow microphone access for this site in your browser settings, then try again.","service-not-allowed":"The browser’s speech service is unavailable. Try Chrome or Edge, or use your device keyboard’s microphone.","audio-capture":"No microphone was found. Connect or enable a microphone, then try again.","no-speech":"No speech was heard. Check your microphone and speak after ‘Listening…’ appears.",network:"The browser’s speech service could not connect. Check your internet connection or use your keyboard microphone."};notice.textContent=messages[e.error]||"Voice input failed ("+(e.error||"unknown error")+"). Check microphone permission or type your request.";};
  recog.onend=()=>{voice.disabled=false;};
  try{recog.start();}catch(error){voice.disabled=false;notice.textContent=error.name==="NotAllowedError"?"Microphone access is blocked. Allow microphone access for this site, then try again.":"Voice input could not start. Refresh the page and try again, or type your request.";}
 });
}
function initEasyHelp(){
 const makeMapLink=origin=>{const link=$("mapDirections");link.href="https://www.google.com/maps/search/?api=1&query="+encodeURIComponent("Sampark Centre near "+origin+", Chandigarh");link.hidden=false;};
 $("locateCentre").addEventListener("click",()=>{if(!navigator.geolocation){$("locationNotice").textContent="Location is unavailable in this browser. Enter your sector below.";return;}$("locationNotice").textContent="Finding your location…";navigator.geolocation.getCurrentPosition(pos=>{makeMapLink(pos.coords.latitude+","+pos.coords.longitude);$("locationNotice").textContent="Nearby results are ready. Your location is shared with Maps only if you open the link.";},()=>{$("locationNotice").textContent="Could not access your location. Enter your sector below.";},{enableHighAccuracy:false,timeout:10000,maximumAge:120000});});
 $("manualDirections").addEventListener("click",()=>{const place=$("manualOrigin").value.trim();if(!place){$("locationNotice").textContent="Enter a sector or area first.";return;}makeMapLink(place);$("locationNotice").textContent="Nearby results are ready. Open Maps to see them.";});
 $("checkStatus").addEventListener("click",async()=>{const id=$("statusId").value.trim().toUpperCase();if(!id){$("statusResult").textContent="Enter your tracking number first.";return;}$("checkStatus").disabled=true;$("statusResult").textContent="Checking your request…";$("statusHistory").replaceChildren();$("speakStatus").disabled=true;$("helpSignIn").hidden=true;try{const item=await api("/api/my/requests/"+encodeURIComponent(id));const statusName=statuses[item.status]||item.status;const spoken="Your "+item.kind+" request, number "+item.id+", is "+statusName.replaceAll("_"," ")+(item.history?.at(-1)?.note?". Latest update: "+item.history.at(-1).note:"");$("statusResult").textContent=spoken;const list=node("ol",undefined,"timeline");(item.history||[]).forEach(row=>{const li=node("li");li.append(node("b",statuses[row.status]||row.status),node("small",new Date(row.created_at).toLocaleString()),node("p",row.note||""));list.append(li);});$("statusHistory").append(list);$("speakStatus").disabled=false;$("lastStatusText").textContent=spoken;}catch(error){$("statusResult").textContent=error.message;if(error.message.toLowerCase().includes("sign in"))$("helpSignIn").hidden=false;}finally{$("checkStatus").disabled=false;}});
 $("speakStatus").addEventListener("click",()=>{if(!window.speechSynthesis){$("statusResult").textContent="Read-aloud is not supported in this browser.";return;}window.speechSynthesis.cancel();window.speechSynthesis.speak(new SpeechSynthesisUtterance($("lastStatusText").textContent));});
}
function initAuth(){
 const signup=location.pathname==="/sign-up";
 $("authTitle").innerHTML=signup?"Create your <em>account.</em>":"Welcome <em>back.</em>";
 $("authSubmit").textContent=signup?"Create account":"Sign in";
 $("password").autocomplete=signup?"new-password":"current-password";
 if(signup){$("fullName").hidden=false;$("nameLabel").hidden=false;$("fullName").required=true;$("passwordHint").hidden=false;}
 $("authSwitch").replaceChildren(document.createTextNode(signup?"Already have an account? ":"New to CivicSathi? "));
 const link=node("a",signup?"Sign in":"Create an account");link.href=signup?"/sign-in":"/sign-up";$("authSwitch").append(link);
 $("authForm").addEventListener("submit",async event=>{
  event.preventDefault();$("authSubmit").disabled=true;$("authNotice").textContent="Checking your details…";
  try{const body={email:$("email").value,password:$("password").value};const result=signup?await post("/api/auth/register",{...body,full_name:$("fullName").value}):await post("/api/auth/login",body);
   const next=new URLSearchParams(location.search).get("next");location.href=next&&next.startsWith("/")&&!next.startsWith("//")?next:(result.user.role==="staff"?"/staff":"/account");
  }catch(e){$("authNotice").textContent=e.message;}finally{$("authSubmit").disabled=false;}
 });
}
async function initProfile(){
 const form=$("profileForm"),fields={full_name:$("profileName"),phone:$("profilePhone"),address:$("profileAddress")},status=$("profileStatus");
 try{
  const profile=await api("/api/profile");$("profileEmail").textContent=profile.email;
  fields.full_name.value=profile.full_name||"";fields.phone.value=profile.phone||"";fields.address.value=profile.address||"";
  let saved=Object.fromEntries(Object.entries(fields).map(([key,input])=>[key,input.value]));let timer=null,inFlight=false,queued=false;
  const save=async()=>{
   clearTimeout(timer);const values=Object.fromEntries(Object.entries(fields).map(([key,input])=>[key,input.value.trim()]));
   const changes=Object.fromEntries(Object.entries(values).filter(([key,value])=>value!==saved[key]));
   if(!Object.keys(changes).length){status.textContent="All changes saved.";return;}
   if(inFlight){queued=true;return;}inFlight=true;queued=false;status.textContent="Saving your profile…";
   let succeeded=false;try{const updated=await api("/api/profile",{method:"PATCH",body:JSON.stringify(changes)});saved={full_name:updated.full_name||"",phone:updated.phone||"",address:updated.address||""};succeeded=true;status.textContent="Saved to your profile.";}
   catch(error){queued=false;status.textContent="Could not save: "+error.message+". Edit a field or press Save now to retry.";}
   finally{inFlight=false;const latest=Object.fromEntries(Object.entries(fields).map(([key,input])=>[key,input.value.trim()]));if(succeeded&&(queued||Object.keys(latest).some(key=>latest[key]!==saved[key])))timer=setTimeout(save,250);}
  };
  form.addEventListener("input",()=>{status.textContent="Unsaved changes…";clearTimeout(timer);timer=setTimeout(save,700);});
  Object.values(fields).forEach(input=>input.addEventListener("blur",save));
  form.addEventListener("submit",event=>{event.preventDefault();save();});
 }catch(error){status.textContent="Could not load your profile: "+error.message;}
}
async function loadServices(){
 try{services=await api("/api/services");renderServices();}
 catch(e){$("services").textContent="Unable to load the civic directory: "+e.message;}
}
function renderServices(){
 const query=($("serviceSearch")?.value||"").toLowerCase(),wrap=$("services");wrap.replaceChildren();
 services.filter(s=>(s.name+" "+s.description+" "+s.category).toLowerCase().includes(query)).forEach(s=>{
  const card=node("article",undefined,"service-card");
  card.append(node("span",categories[s.category]||s.category,"card-number"),node("h2",s.name),node("p",s.description));
  if(s.category==="centres"){
   const map=node("a","Open Sampark Centres in Maps ↗");map.href="https://www.google.com/maps/search/?api=1&query=Sampark+Centre+Chandigarh";map.target="_blank";map.rel="noopener noreferrer";card.append(map);
   const official=node("a","Official services and centre details ↗");official.href=s.source;official.target="_blank";official.rel="noopener noreferrer";official.className="official-link";card.append(official);wrap.append(card);return;
  }
  const a=node("a",s.action?"Start a demo request →":s.category==="social_welfare"?"Explore requests →":"Visit official information ↗");
  if(s.action){a.href="/apply?service="+encodeURIComponent(s.action);}else if(s.category==="social_welfare"){a.href="/apply?service=social_welfare";}else{a.href=s.source;a.target="_blank";a.rel="noopener noreferrer";}card.append(a);wrap.append(card);
 });
 if(!wrap.children.length)wrap.append(node("p","No services match that search.","muted"));
}
$("serviceSearch")?.addEventListener("input",renderServices);
function initReport(){
 initVoiceInput("reportVoiceInput","issue","reportVoiceLanguage","reportVoiceNotice");
 Object.entries(categories).forEach(([value,label])=>{const o=node("option",label);o.value=value;$("category").append(o);});
 const routedDraft=readRoutedDraft();if(routedDraft){
  currentDraft=routedDraft;$("issue").value=routedDraft.source_text||routedDraft.summary||"";$("category").value=routedDraft.category||"other";
  $("summary").value=routedDraft.summary||"";$("location").value=routedDraft.location||"";
  $("meta").textContent="Details from Ask CivicSathi are filled in. Review and edit them; add a location if missing.";
  $("matchedService").textContent="Suggested service: "+(lookupCategory(routedDraft.category)||"Civic service")+". This remains a demo request.";
  $("result").hidden=false;$("notice").textContent="AI draft loaded. Check the category, summary and location, then confirm before submitting.";
 }
 $("photo").addEventListener("change",()=>{
  clearPhoto();const f=$("photo").files[0];if(!f)return;
  if(!["image/jpeg","image/png","image/webp"].includes(f.type)||f.size>2500000){$("photoResult").textContent="Choose a JPG, PNG or WebP image up to 2.5 MB.";$("photo").value="";return;}
  const reader=new FileReader();reader.onload=()=>{photoData=String(reader.result);$("photoPreview").src=photoData;$("photoPreview").hidden=false;$("photoResult").textContent="Photo ready. Agree to analysis before sending it to Google.";};reader.readAsDataURL(f);
 });
 $("removePhoto").addEventListener("click",()=>{$("photo").value="";clearPhoto();});
 $("photoConsent").addEventListener("change",()=>{if(!$("photoConsent").checked&&photoId){photoId=null;$("photoResult").textContent="Consent withdrawn. Analyze again to create a new draft.";}});
 $("photoAnalyze").addEventListener("click",()=>withBusy(analyzePhoto));
 $("analyze").addEventListener("click",()=>withBusy(async()=>{
  if($("photo").files[0]){if(!$("photoConsent").checked)throw Error("Agree to photo processing first.");if(!photoId)await analyzePhoto();}
  if(!$("issue").value.trim()&&!photoId)throw Error("Describe the issue or add a photograph.");
  const data=await post("/api/intake",{text:$("issue").value.trim(),photo_id:photoId});
  currentDraft=data.draft;$("category").value=currentDraft.category;$("summary").value=currentDraft.summary;$("location").value=currentDraft.location||"";
  $("meta").textContent="Missing details: "+(currentDraft.missing_fields.join(", ")||"none identified")+". AI findings need your review.";
  $("matchedService").textContent="Suggested service: "+(data.service?.name||"Choose an appropriate civic service.");
  drawDuplicates(data.possible_duplicates||[]);$("result").hidden=false;$("notice").textContent=data.mode==="safe-fallback"?"AI is unavailable. A basic suggestion was generated; please review it carefully.":"Draft prepared. Check the facts and location.";
 }));
 ["category","summary","location"].forEach(id=>$(id).addEventListener("input",()=>{ $("confirm").checked=false;$("duplicates").textContent="Details changed. Recheck before submitting."; }));
 $("checkDuplicates").addEventListener("click",async()=>{try{drawDuplicates(await post("/api/duplicates",draftFromForm()));}catch(e){$("duplicates").textContent=e.message;}});
 $("submit").addEventListener("click",()=>withBusy(async()=>{
  const draft=draftFromForm();if(!draft.location||!draft.summary||draft.category==="other")throw Error("Add a summary, choose a category and provide a location.");
  if(!$("confirm").checked)throw Error("Confirm the details before submitting.");
  const item=await post("/api/cases",{draft,confirmed:true,request_id:requestId});
  $("reportSuccessId").textContent="Tracking number: "+item.id;
  const panel=document.querySelector(".columns > .panel");Array.from(panel.children).forEach(child=>{if(child!==$("reportSuccess"))child.hidden=true;});$("reportSuccess").hidden=false;
  $("submit").disabled=true;
 }));
 $("newComplaint").addEventListener("click",()=>location.reload());
}
async function withBusy(fn){
 if(busy)return;busy=true;["analyze","photoAnalyze","submit","photo","issue","photoConsent"].forEach(id=>{const e=$(id);if(e)e.disabled=true;});
 try{await fn();}catch(e){const target=$("notice")||$("photoResult")||$("authNotice");if(target)target.textContent=e.message;}
 finally{busy=false;["analyze","photoAnalyze","submit","photo","issue","photoConsent"].forEach(id=>{const e=$(id);if(e)e.disabled=false;});}
}
function clearPhoto(){photoId=null;photoData="";if($("photoPreview")){$("photoPreview").hidden=true;$("photoPreview").removeAttribute("src");}if($("photoResult"))$("photoResult").textContent="";}
async function analyzePhoto(){
 if(!$("photo").files[0]||!photoData)throw Error("Choose a photo and wait for the preview.");
 if(!$("photoConsent").checked)throw Error("Please agree to photo processing.");
 $("photoResult").textContent="Gemma 4 is analyzing the photo…";
 const f=$("photo").files[0],result=await post("/api/analyze-photo",{image_base64:photoData.split(",")[1],mime_type:f.type,text:$("issue").value.trim()});
 photoId=result.photo_id;
 if(result.analysis_available){const a=result.analysis;$("photoResult").textContent=a.description+"\nSuggested category: "+(categories[a.category]||a.category)+(a.uncertainty?"\nUncertainty: "+a.uncertainty:"")+(a.follow_up_question?"\n"+a.follow_up_question:"");}
 else $("photoResult").textContent="Google image analysis is unavailable ("+result.reason+"). You can describe the issue and continue.";
}
function draftFromForm(){const {source_text,...draft}=currentDraft||{};return {...draft,category:$("category").value,summary:$("summary").value.trim(),location:$("location").value.trim()||null};}
function drawDuplicates(items){$("duplicates").textContent=items.length?"Potential matches: "+items.map(x=>x.id+" ("+Math.round(x.score*100)+"%)").join(", ")+". Compare locations before deciding.":"No likely matches among your recent reports.";}
function renderCase(item){
 const card=node("article",undefined,"case-card");card.append(node("span",statuses[item.status]||item.status,"badge"),node("p",item.id,"case-id"),node("h2",item.summary),node("p",item.location,"muted"));
 if(item.photo_id){const img=node("img");img.src="/api/photos/"+encodeURIComponent(item.photo_id);img.alt="Your complaint photo";img.className="evidence-photo";card.append(img);}
 const timeline=node("ol",undefined,"timeline");(item.history||[]).forEach(h=>{const li=node("li");li.append(node("b",statuses[h.status]||h.status),node("small",new Date(h.created_at).toLocaleString()),node("p",h.note||""));timeline.append(li);});card.append(timeline);return card;
}
function renderServiceRequest(item){
 const card=node("article",undefined,"case-card"),labels={health_appointment:"GMSH-16 appointment request",senior_card:"Senior citizen card",disability_card:"Disability identity card",old_age_pension:"Old-age pension application",widow_pension:"Widow pension application",disability_pension:"Disability pension application",horticulture:"Horticulture request"};
 card.append(node("span",statuses[item.status]||item.status,"badge"),node("p",item.id,"case-id"),node("h2",labels[item.service_type]||item.service_type),node("p",item.applicant_name+" · "+item.contact_phone,"muted"));
 const lines=Object.entries(item.details||{}).filter(([k])=>k!=='description').map(([k,v])=>k.replaceAll('_',' ')+": "+v);
 if(item.details?.description)lines.push(item.details.description);if(lines.length)card.append(node("p",lines.join(" · "),"helper"));
 const note=node("p","Demo tracking only. Contact the relevant office to confirm official processing.","helper");card.append(note);
 const timeline=node("ol",undefined,"timeline");(item.history||[]).forEach(h=>{const li=node("li");li.append(node("b",statuses[h.status]||h.status),node("small",new Date(h.created_at).toLocaleString()),node("p",h.note||""));timeline.append(li);});card.append(timeline);return card;
}
async function loadMyCases(){
 try{const items=await api("/api/my/cases");$("trackNotice").textContent=items.length?items.length+" report(s) in your account.":"No reports yet. When you submit one, it will appear here.";items.forEach(i=>$("myCases").append(renderCase(i)));}
 catch(e){$("trackNotice").textContent=e.message;}
}
async function loadMyRequests(){try{const items=await api("/api/my/service-requests");$("requestNotice").textContent=items.length?items.length+" service request(s) on your account.":"No service requests yet.";items.forEach(i=>$("myRequests").append(renderServiceRequest(i)));}catch(e){$("requestNotice").textContent=e.message;}}
function initServiceRequest(){
 const select=$("serviceType"),allowed={health_appointment:["health_appointment"],social_welfare:["senior_card","disability_card","old_age_pension","widow_pension","disability_pension"],horticulture:["horticulture"]},titles={health_appointment:"Government hospital appointment",social_welfare:"Social welfare application",horticulture:"Horticulture request"};
 const initial=new URLSearchParams(location.search).get("service")||"health_appointment",group=Object.keys(allowed).find(key=>key===initial||allowed[key].includes(initial))||"health_appointment";
 $("applyTitle").textContent=titles[group];if(group==="social_welfare")$("welfareFields").hidden=false;if(group==="horticulture")$("horticultureFields").hidden=false;if(group==="health_appointment")$("healthFields").hidden=false;
 select.replaceChildren();(allowed[group]||allowed.health_appointment).forEach(type=>{const o=node("option",({senior_card:"Senior citizen card",disability_card:"Disability identity card",old_age_pension:"Old-age pension",widow_pension:"Widow pension",disability_pension:"Disability pension",health_appointment:"GMSH-16 appointment",horticulture:"Horticulture request"})[type]);o.value=type;select.append(o);});
 const routedDraft=readRoutedDraft();if(routedDraft){
  const fields=routedDraft.extracted_fields||{};
  if(routedDraft.service_type&&Array.from(select.options).some(option=>option.value===routedDraft.service_type))select.value=routedDraft.service_type;
  $("applicantName").value=fields.applicant_name||me?.full_name||"";$("phone").value=fields.contact_phone||me?.phone||"";
  if(group==="health_appointment"){$("department").value=fields.department||"";$("preferredDate").value=fields.preferred_date||"";$("visitReason").value=fields.reason||routedDraft.summary||"";}
  else if(group==="social_welfare"){$("beneficiaryName").value=fields.beneficiary_name||"";$("relationship").value=fields.relationship||"Self";$("welfareAddress").value=fields.address||routedDraft.location||me?.address||"";$("welfareDescription").value=fields.description||routedDraft.summary||"";$("welfareKind").textContent=select.options[select.selectedIndex].text;}
  else if(group==="horticulture"){$("requestLocation").value=routedDraft.location||fields.address||"";$("requestDescription").value=fields.description||routedDraft.summary||"";}
  $("requestNotice").textContent="AI-filled details are ready. Review them, complete any missing required fields, then confirm before saving.";
 }
 select.addEventListener("change",()=>{$("welfareKind").textContent=select.options[select.selectedIndex].text;});
 $("serviceRequestForm").addEventListener("submit",async e=>{e.preventDefault();const type=select.value,details={};if(type==="health_appointment"){details.department=$("department").value;details.preferred_date=$("preferredDate").value;details.reason=$("visitReason").value.trim();}else if(type==="horticulture"){details.location=$("requestLocation").value.trim();details.description=$("requestDescription").value.trim();if(!details.location||!details.description){$("requestNotice").textContent="Add the location and a short description.";return;}}else{details.beneficiary_name=$("beneficiaryName").value.trim();details.relationship=$("relationship").value;details.address=$("welfareAddress").value.trim();details.description=$("welfareDescription").value.trim();if(!details.beneficiary_name){$("requestNotice").textContent="Enter the beneficiary name.";return;}}
  const submit=$("requestSubmit");submit.disabled=true;$("requestNotice").textContent="Saving your demo request…";try{const result=await post("/api/service-requests",{service_type:type,applicant_name:$("applicantName").value.trim(),contact_phone:$("phone").value.trim(),details});$("serviceSuccessId").textContent="Tracking number: "+result.id;$("serviceRequestForm").hidden=true;$("serviceSuccess").hidden=false;}catch(err){$("requestNotice").textContent=err.message;}finally{submit.disabled=false;}
 });
}
function readRoutedDraft(){try{const raw=sessionStorage.getItem("civicsathi-intake-draft");if(!raw)return null;sessionStorage.removeItem("civicsathi-intake-draft");return JSON.parse(raw);}catch(_){sessionStorage.removeItem("civicsathi-intake-draft");return null;}}
function lookupCategory(category){return categories[category]||null;}
async function initAccount(){
 $("accountName").textContent=me.full_name.split(" ")[0]+"."; $("accountEmail").textContent=me.email;
 $("logout").addEventListener("click",async()=>{await post("/api/auth/logout",{});location.href="/";});
 const items=await api("/api/my/cases");if(!items.length)$("accountCases").textContent="No reports yet.";
 items.slice(0,5).forEach(i=>$("accountCases").append(renderCase(i)));
}
function initStaff(){
 $("staffLogout").addEventListener("click",async()=>{await post("/api/auth/logout",{});location.href="/";});
 $("refreshStaff").addEventListener("click",()=>{loadStaff();loadStaffRequests();});loadStaff();loadStaffRequests();
}
async function loadStaff(){
 try{const data=await api("/api/admin/cases");const wrap=$("staffCases");wrap.replaceChildren();$("staffNotice").textContent=data.cases.length+" recent cases.";
 data.cases.forEach(item=>{
  const card=node("article",undefined,"staff-card");card.append(node("span",statuses[item.status],"badge"),node("p",item.id,"case-id"),node("h2",item.summary),node("p",item.location,"muted"));
  if(item.user_id)card.append(node("p","Citizen account: "+(item.user_id.slice(0,8)),"helper"));
  const select=node("select");select.setAttribute("aria-label","Status for "+item.id);(data.transitions[item.status]||[]).forEach(s=>{const o=node("option",statuses[s]);o.value=s;select.append(o);});
  const note=node("textarea");note.placeholder="Progress note (required for resolved/rejected)";
  const save=node("button","Save update","secondary"),msg=node("p",undefined,"status-message");
  save.addEventListener("click",async()=>{save.disabled=true;try{await api("/api/admin/cases/"+encodeURIComponent(item.id),{method:"PATCH",body:JSON.stringify({status:select.value,note:note.value.trim()})});await loadStaff();}catch(e){msg.textContent=e.message;}finally{save.disabled=false;}});
  card.append(select,note,save,msg);wrap.append(card);
 });}catch(e){$("staffNotice").textContent=e.message;}
}
async function loadStaffRequests(){try{const data=await api("/api/admin/service-requests"),wrap=$("staffRequests");wrap.replaceChildren();$("serviceRequestCount").textContent=data.requests.length+" recent service requests.";data.requests.forEach(item=>{
 const card=node("article",undefined,"staff-card");card.append(node("span",statuses[item.status]||item.status,"badge"),node("p",item.id,"case-id"),node("h2",(data.labels[item.service_type]||item.service_type)+" · "+item.applicant_name),node("p",item.contact_phone,"muted"));
 const detail=Object.entries(item.details||{}).map(([k,v])=>k.replaceAll("_"," ")+": "+v).join(" · ");if(detail)card.append(node("p",detail,"helper"));const select=node("select"),transitions=data.transitions[item.status]||[];transitions.forEach(s=>{const o=node("option",statuses[s]);o.value=s;select.append(o);});const note=node("textarea");note.placeholder="Progress note (required for resolved/rejected)";const save=node("button","Save update","secondary"),msg=node("p",undefined,"status-message");save.addEventListener("click",async()=>{save.disabled=true;try{await api("/api/admin/service-requests/"+encodeURIComponent(item.id),{method:"PATCH",body:JSON.stringify({status:select.value,note:note.value.trim()})});await loadStaffRequests();}catch(e){msg.textContent=e.message;}finally{save.disabled=false;}});card.append(select,note,save,msg);wrap.append(card);
 });}catch(e){$("serviceRequestCount").textContent=e.message;}}
bootstrap();

