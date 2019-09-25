package main

import ("net/http")
import ("os/exec")
import ("bytes"
        "log"
        "strings"
	"runtime"
        )

func main(){
    http.HandleFunc("/restoreClient/",restoreClient)
    http.HandleFunc("/cleanup/",cleanup)
    http.ListenAndServe(":7777",nil)
}

//checks if the request comes from a allowed ip, only bui's should access the api loclahost networker buis
func checkPermission(toCheck *http.Request) bool{
 if strings.Contains(toCheck.RemoteAddr,"<IP Address>") || strings.Contains(toCheck.RemoteAddr,"<IP Address>") || strings.Contains(toCheck.RemoteAddr,"<IP Address>"){
  return true
 }
  log.Print("Access got denied for: " + toCheck.RemoteAddr)
  return false
}

//formats a specific volume
func cleanup(w http.ResponseWriter, r *http.Request){
 if checkPermission(r){
	harddrive := r.URL.Query().Get("harddrive")
	if harddrive != ""{
		ps, _ :=exec.LookPath("powershell.exe")
		cmd := exec.Command(ps,"Format-Volume "+harddrive+" -filesystem ntfs -Confirm:$false")
		var out bytes.Buffer
		var sterr bytes.Buffer
		cmd.Stdout = &out
		cmd.Stderr = &sterr
		err := cmd.Run()
		if err == nil{
		 w.Write([]byte(out.String()))
		}else{
		 log.Print("Error happend in cleanup: " + err.Error() + sterr.String())
		 http.Error(w,out.String()+" " + sterr.String() + " " + err.Error(),500)
		}
	}else{
		w.Write([]byte("Please specify following parameter harddrive"))
	}
 }else{
    http.Error(w,"Access denied",500)
 }
}

// Handles the restore form a backup to a specified harddrive
func restoreClient(w http.ResponseWriter, r *http.Request){
 if checkPermission(r){
    r.ParseForm()
    log.Printf("len: %d", r.Header.Get("content-length"))
    ssid := r.URL.Query().Get("ssid")
    cloneid := r.URL.Query().Get("cloneid")
    harddrive := r.URL.Query().Get("harddrive")
    message := "SSID:" + ssid+" CloneId: " + cloneid+" harddrive: "+ harddrive
    if ssid != "" && cloneid != "" && harddrive != "" {
	cmd := exec.Command("")
	if runtime.GOOS == "windows" {
        cmd = exec.Command("C:\\Program Files\\EMC NetWorker\\nsr\\bin\\recover","-iY","-f","-S"+ ssid+"/"+cloneid,"-r"+harddrive)
	}else{
        cmd = exec.Command("recover","-iY","-f","-S"+ ssid+"/"+cloneid,"-r"+harddrive)
	}
        var out bytes.Buffer
        var sterr bytes.Buffer
        cmd.Stdout = &out
        cmd.Stderr = &sterr
        err := cmd.Run()
        if err == nil {
        w.Write([]byte("\n" + out.String() + sterr.String()))
	}else{
        log.Print("Error happend in restoreClient" + err.Error() + sterr.String())
	http.Error(w,message + out.String()+" " + sterr.String() + " " + err.Error(),501)
	}
    }else{
        w.Write([]byte("Please sepcify following parameters ssid , cloneid , harddrive"))
    }
 }else{
    http.Error(w,"Access denied",401)
 }
}
