/* Geometry and PNG conversion run in the local Python process. */
class PythonEngine {
  constructor(status){this.status=status;this.ready=false;this.pythonPNG=false;}
  async initialize(){const health=await this.fetch('/api/health');this.pythonPNG=health.png;this.ready=true;this.status('Local Python','ready');}
  async fetch(url,payload,blob=false){
    const response=await fetch(url,payload===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    if(!response.ok){const value=await response.json();throw Error(value.error?.message||value.error||'Request failed.');}
    return blob?response.blob():response.json();
  }
  request(payload){return this.fetch('/api/render',payload);}
  png(asset,options,scale){return this.fetch('/api/png',{asset,options,scale},true);}
}
