package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"time"
)

type options struct {
	host         string
	port         int
	pythonURL    string
	pythonScript string
	pythonBin    string
	appDir       string
	staticDir    string
	runtimeDir   string
}

func parseOptions(args []string) (options, error) {
	fs := flag.NewFlagSet("kaguya-go-backend", flag.ContinueOnError)
	var opt options
	fs.StringVar(&opt.host, "host", "127.0.0.1", "HTTP listen host")
	fs.IntVar(&opt.port, "port", 8766, "HTTP listen port")
	fs.StringVar(&opt.pythonURL, "python-url", "", "Existing Python worker base URL")
	fs.StringVar(&opt.pythonScript, "python-script", "", "Optional Python worker script to start")
	fs.StringVar(&opt.pythonBin, "python", "python", "Python executable")
	fs.StringVar(&opt.appDir, "app-dir", "", "Legacy python-app resource directory for assets")
	fs.StringVar(&opt.staticDir, "static-dir", "", "Go backend static directory")
	fs.StringVar(&opt.runtimeDir, "runtime-dir", "", "Runtime data directory")
	if err := fs.Parse(args); err != nil {
		return opt, err
	}
	if opt.runtimeDir == "" {
		wd, err := os.Getwd()
		if err != nil {
			return opt, err
		}
		opt.runtimeDir = filepath.Join(wd, "runtime")
	}
	return opt, nil
}

func main() {
	opt, err := parseOptions(os.Args[1:])
	if err != nil {
		log.Fatal(err)
	}
	var pythonCmd *exec.Cmd
	if opt.pythonURL == "" && opt.pythonScript != "" {
		pythonPort, err := freePort()
		if err != nil {
			log.Printf("python worker start skipped: %v", err)
		} else if cmd, err := startPythonWorker(context.Background(), opt.pythonScript, opt.runtimeDir, opt.pythonBin, pythonPort); err != nil {
			log.Printf("python worker start skipped: %v", err)
		} else {
			pythonCmd = cmd
			opt.pythonURL = "http://127.0.0.1:" + strconv.Itoa(pythonPort)
			if err := waitForHTTP(opt.pythonURL+"/", 45*time.Second); err != nil {
				log.Printf("python worker health check failed: %v", err)
			}
		}
	}
	if pythonCmd != nil && pythonCmd.Process != nil {
		defer func() { _ = pythonCmd.Process.Kill() }()
	}
	srv, err := NewServer(ServerConfig{
		RuntimeDir: opt.runtimeDir,
		PythonURL:  opt.pythonURL,
		AppDir:     opt.appDir,
		StaticDir:  opt.staticDir,
		BindHost:   opt.host,
	})
	if err != nil {
		log.Fatal(err)
	}
	addr := net.JoinHostPort(opt.host, fmt.Sprintf("%d", opt.port))
	log.Printf("kaguya go backend listening on http://%s", addr)
	log.Fatal(http.ListenAndServe(addr, srv.Handler()))
}

func startPythonWorker(ctx context.Context, script, runtimeDir, pythonBin string, port int) (*exec.Cmd, error) {
	abs, err := filepath.Abs(script)
	if err != nil {
		return nil, err
	}
	if _, err := os.Stat(abs); err != nil {
		return nil, err
	}
	cmd := exec.CommandContext(ctx, pythonBin, abs, "--port", strconv.Itoa(port), "--localhost-only")
	cmd.Dir = filepath.Dir(abs)
	cmd.Env = append(os.Environ(),
		"KAGUYA_RUNTIME_DIR="+filepath.Join(runtimeDir, "python-app"),
		"KAGUYA_DESKTOP_MODE=1",
		"KAGUYA_ELECTRON=1",
		"KAGUYA_DISABLE_NGROK=1",
		"KAGUYA_PORT="+strconv.Itoa(port),
	)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd, cmd.Start()
}

func freePort() (int, error) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		return 0, err
	}
	defer ln.Close()
	return ln.Addr().(*net.TCPAddr).Port, nil
}

func waitForHTTP(rawURL string, timeout time.Duration) error {
	deadline := time.Now().Add(timeout)
	client := http.Client{Timeout: 700 * time.Millisecond}
	var last error
	for time.Now().Before(deadline) {
		resp, err := client.Get(rawURL)
		if err == nil {
			_ = resp.Body.Close()
			if resp.StatusCode < 500 {
				return nil
			}
			last = fmt.Errorf("status %d", resp.StatusCode)
		} else {
			last = err
		}
		time.Sleep(300 * time.Millisecond)
	}
	return last
}
