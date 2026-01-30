//go:build !windows

package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"syscall"
)

// daemonSysProcAttr returns the syscall attributes for detaching the daemon process
func daemonSysProcAttr() *syscall.SysProcAttr {
	return &syscall.SysProcAttr{
		Setsid: true,
	}
}

// isServiceInstalled checks if the daemon is installed as an OS service
func isServiceInstalled() (bool, string) {
	if runtime.GOOS == "darwin" {
		// Check launchd
		plistPath := getLaunchdPlistPath()
		if _, err := os.Stat(plistPath); err == nil {
			return true, "launchd"
		}
	} else {
		// Check systemd (user)
		servicePath := getSystemdServicePath()
		if _, err := os.Stat(servicePath); err == nil {
			return true, "systemd"
		}
	}
	return false, ""
}

func getLaunchdPlistPath() string {
	home, _ := os.UserHomeDir()
	return filepath.Join(home, "Library", "LaunchAgents", "com.iatf.daemon.plist")
}

func getSystemdServicePath() string {
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ".config", "systemd", "user", "iatf-daemon.service")
}

func daemonInstallCommand() int {
	if runtime.GOOS == "darwin" {
		return installLaunchdService()
	}
	return installSystemdService()
}

func daemonUninstallCommand() int {
	if runtime.GOOS == "darwin" {
		return uninstallLaunchdService()
	}
	return uninstallSystemdService()
}

func installSystemdService() int {
	execPath, err := os.Executable()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error getting executable path: %v\n", err)
		return 1
	}

	serviceContent := fmt.Sprintf(`[Unit]
Description=IATF File Watcher Daemon
After=network.target

[Service]
Type=simple
ExecStart=%s daemon run
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
`, execPath)

	servicePath := getSystemdServicePath()
	serviceDir := filepath.Dir(servicePath)

	// Create directory
	if err := os.MkdirAll(serviceDir, 0755); err != nil {
		fmt.Fprintf(os.Stderr, "Error creating service directory: %v\n", err)
		return 1
	}

	// Write service file
	if err := os.WriteFile(servicePath, []byte(serviceContent), 0644); err != nil {
		fmt.Fprintf(os.Stderr, "Error writing service file: %v\n", err)
		return 1
	}

	// Reload systemd
	cmd := exec.Command("systemctl", "--user", "daemon-reload")
	if err := cmd.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "Warning: Failed to reload systemd: %v\n", err)
	}

	// Enable service
	cmd = exec.Command("systemctl", "--user", "enable", "iatf-daemon")
	if err := cmd.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "Warning: Failed to enable service: %v\n", err)
	}

	fmt.Println("Service installed (systemd user service)")
	fmt.Println("\nTo start the service now:")
	fmt.Println("  systemctl --user start iatf-daemon")
	fmt.Println("\nTo check status:")
	fmt.Println("  systemctl --user status iatf-daemon")
	return 0
}

func uninstallSystemdService() int {
	servicePath := getSystemdServicePath()

	// Stop service if running
	cmd := exec.Command("systemctl", "--user", "stop", "iatf-daemon")
	cmd.Run() // Ignore error - service may not be running

	// Disable service
	cmd = exec.Command("systemctl", "--user", "disable", "iatf-daemon")
	cmd.Run() // Ignore error - service may not be enabled

	// Remove service file
	if err := os.Remove(servicePath); err != nil {
		if os.IsNotExist(err) {
			fmt.Println("Service not installed")
			return 0
		}
		fmt.Fprintf(os.Stderr, "Error removing service file: %v\n", err)
		return 1
	}

	// Reload systemd
	cmd = exec.Command("systemctl", "--user", "daemon-reload")
	cmd.Run()

	fmt.Println("Service uninstalled")
	return 0
}

func installLaunchdService() int {
	execPath, err := os.Executable()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error getting executable path: %v\n", err)
		return 1
	}

	home, _ := os.UserHomeDir()
	logPath := getDaemonLogPath()

	plistContent := fmt.Sprintf(`<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.iatf.daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>%s</string>
        <string>daemon</string>
        <string>run</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>%s</string>
    <key>StandardErrorPath</key>
    <string>%s</string>
    <key>WorkingDirectory</key>
    <string>%s</string>
</dict>
</plist>
`, execPath, logPath, logPath, home)

	plistPath := getLaunchdPlistPath()
	plistDir := filepath.Dir(plistPath)

	// Create directory
	if err := os.MkdirAll(plistDir, 0755); err != nil {
		fmt.Fprintf(os.Stderr, "Error creating LaunchAgents directory: %v\n", err)
		return 1
	}

	// Write plist file
	if err := os.WriteFile(plistPath, []byte(plistContent), 0644); err != nil {
		fmt.Fprintf(os.Stderr, "Error writing plist file: %v\n", err)
		return 1
	}

	// Load the service
	cmd := exec.Command("launchctl", "load", plistPath)
	if output, err := cmd.CombinedOutput(); err != nil {
		// Check if already loaded
		if !strings.Contains(string(output), "already loaded") {
			fmt.Fprintf(os.Stderr, "Warning: Failed to load service: %v\n%s\n", err, output)
		}
	}

	fmt.Println("Service installed (launchd)")
	fmt.Println("\nThe service will start automatically on login.")
	fmt.Println("\nTo start now:")
	fmt.Println("  launchctl start com.iatf.daemon")
	fmt.Println("\nTo check status:")
	fmt.Println("  launchctl list | grep iatf")
	return 0
}

func uninstallLaunchdService() int {
	plistPath := getLaunchdPlistPath()

	// Unload the service
	cmd := exec.Command("launchctl", "unload", plistPath)
	cmd.Run() // Ignore error - service may not be loaded

	// Remove plist file
	if err := os.Remove(plistPath); err != nil {
		if os.IsNotExist(err) {
			fmt.Println("Service not installed")
			return 0
		}
		fmt.Fprintf(os.Stderr, "Error removing plist file: %v\n", err)
		return 1
	}

	fmt.Println("Service uninstalled")
	return 0
}
