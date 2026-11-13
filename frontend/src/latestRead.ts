/** Only the newest read may publish a value or an error. Writes never pass here. */
export class LatestRead {
 private generation=0;
 private active=false;
 get pending():boolean{return this.active;}
 invalidate():void{this.generation++;this.active=false;}
 async run<T>(load:()=>Promise<T>,accept:(value:T)=>void,reject:(error:unknown)=>void):Promise<void>{
  const generation=++this.generation;
  this.active=true;
  try{const value=await load();if(generation===this.generation)accept(value);}
  catch(error){if(generation===this.generation)reject(error);}
  finally{if(generation===this.generation)this.active=false;}
 }
}
