/* The browser never recreates icon geometry in JavaScript.
 * CPython and Pyodide run the same engine and renderer source files.
 */
'use strict';
class PythonEngine {
  constructor(boot, onStatus) { this.boot=boot; this.onStatus=onStatus; this.mode=null; this.pythonPNG=false; this.worker=null; this.pending=new Map(); this.serial=0; this.ready=false; this.py=null; this.mainQueue=Promise.resolve(); }
  async initialize() {
    this.ready=false; this.onStatus('Starting Python','loading');
    try {
      if (/^https?:$/.test(location.protocol)) {
        try {
          const response=await fetch('./api/health',{signal:AbortSignal.timeout(2500)});
          const health=await response.json();
          if(response.ok && health.app==='svgdrawer') {
            this.mode='local';this.pythonPNG=!!health.png;this.ready=true;
            this.onStatus('Python · local','ready');return;
          }
        } catch (_) { /* Static hosting uses the browser's Python runtime instead. */ }
      }
      this.mode='pyodide'; this.onStatus('Loading Python runtime','loading');
      if(this.worker) this.worker.terminate();
      const workerSource=`
        let py; let queue=Promise.resolve();
        self.onmessage=event=>{ queue=queue.then(async()=>{
          const {id,action,files,payload,base}=event.data;
          try {
            if(action==='init') {
              const {loadPyodide}=await import(base+'pyodide.mjs');
              py=await loadPyodide({indexURL:base});
              py.FS.mkdirTree('/svgdrawer');
              for(const [name,contents] of Object.entries(files)) {
                const path='/svgdrawer/'+name;
                py.FS.mkdirTree(path.slice(0,path.lastIndexOf('/')));
                py.FS.writeFile(path,contents,{encoding:'utf8'});
              }
              await py.runPythonAsync("import sys, json\\nsys.path.insert(0, '/svgdrawer')\\nfrom engine import handle_request");
              self.postMessage({id,result:{ready:true}});
            } else {
              py.globals.set('_request_json',JSON.stringify(payload));
              const result=py.runPython("json.dumps(handle_request(json.loads(_request_json)), ensure_ascii=False)");
              self.postMessage({id,result:JSON.parse(result)});
            }
          } catch(error) {self.postMessage({id,error:String(error.message||error)});}
        }); };
      `;
      const url=URL.createObjectURL(new Blob([workerSource],{type:'text/javascript'}));
      try {
        try {this.worker=new Worker(url,{type:'module'});}
        catch(error){error.workerStartFailed=true;throw error;}
      this.worker.onmessage=event=>{
        const job=this.pending.get(event.data.id);if(!job)return;
        clearTimeout(job.timer);this.pending.delete(event.data.id);
        event.data.error?job.reject(Error(event.data.error)):job.resolve(event.data.result);
      };
      this.worker.onerror=event=>{
        for(const job of this.pending.values()){clearTimeout(job.timer);const failure=Error(event.message||'Module workers are not available in this context.');failure.workerStartFailed=true;job.reject(failure);}
        this.pending.clear();
      };
        await this.workerRequest({action:'init',files:this.boot.files,base:this.boot.gallery.settings.pyodide_base},180000);
      } catch(error) {
        if(!error.workerStartFailed)throw error;
        // Some file/opaque-origin contexts cannot start module workers. Keep the
        // single-file app usable with the same Python engine on the main thread.
        if(this.worker)this.worker.terminate();this.worker=null;this.pending.clear();
        await this.initializeMainThread();
      }
      finally {URL.revokeObjectURL(url);}
      this.ready=true;this.onStatus('Python · browser','ready');
    } catch(error) {
      this.ready=false;this.mode=null;
      if(this.worker){this.worker.terminate();this.worker=null;}
      for(const job of this.pending.values()){clearTimeout(job.timer);job.reject(error);}this.pending.clear();
      this.onStatus('Python unavailable','error');throw error;
    }
  }
  async initializeMainThread() {
    this.mode='pyodide-main';this.onStatus('Loading Python compatibility mode','loading');
    const base=this.boot.gallery.settings.pyodide_base;
    const {loadPyodide}=await import(base+'pyodide.mjs');
    this.py=await loadPyodide({indexURL:base});
    this.py.FS.mkdirTree('/svgdrawer');
    for(const [name,contents] of Object.entries(this.boot.files)) {
      const path='/svgdrawer/'+name;
      this.py.FS.mkdirTree(path.slice(0,path.lastIndexOf('/')));
      this.py.FS.writeFile(path,contents,{encoding:'utf8'});
    }
    await this.py.runPythonAsync("import sys, json\nsys.path.insert(0, '/svgdrawer')\nfrom engine import handle_request");
  }
  workerRequest(message,timeout=45000) {
    return new Promise((resolve,reject)=>{
      const id=++this.serial;
      const timer=setTimeout(()=>{this.pending.delete(id);reject(Error('Python request timed out. Retry or use the local Python bundle.'));},timeout);
      this.pending.set(id,{resolve,reject,timer});this.worker.postMessage({id,...message});
    });
  }
  async request(payload) {
    if(!this.ready)throw Error('Python is still loading. Wait for the status indicator or start the local server.');
    if(this.mode==='local') {
      const response=await fetch('./api/render',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:AbortSignal.timeout(45000)});
      const result=await response.json();if(!response.ok)throw Error(result.error||'Python render failed.');return result;
    }
    if(this.mode==='pyodide-main') {
      const job=this.mainQueue.then(()=>{
        this.py.globals.set('_request_json',JSON.stringify(payload));
        return JSON.parse(this.py.runPython('json.dumps(handle_request(json.loads(_request_json)), ensure_ascii=False)'));
      });
      this.mainQueue=job.catch(()=>{});return job;
    }
    return this.workerRequest({action:'request',payload});
  }
  async png(asset,options,scale) {
    if(!this.pythonPNG || this.mode!=='local')throw Error('Python PNG requires the local server and CairoSVG.');
    const response=await fetch('./api/png',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({asset,options,scale}),signal:AbortSignal.timeout(45000)});
    if(!response.ok){const data=await response.json();throw Error(data.error||'PNG export failed.');}
    return response.blob();
  }
}
