// File-to-file client for the resident compiler. The BL service owns all
// compilation, source reads, artifact verification, and output publication.
package main

import (
	"encoding/binary"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"net"
	"os"
	"path/filepath"
	"time"
)

func compile() error {
	clean := flag.Bool("clean", false, "force native translation")
	sdk := flag.Bool("sdk", false, "force the exercising SDK control for a qualified boot source")
	flag.Parse()
	if flag.NArg() != 5 {
		return errors.New("usage: repeat-client [-clean|-sdk] SOCKET NAMESPACE LOGICAL_FILENAME SOURCE OUTPUT")
	}
	source, err := filepath.Abs(flag.Arg(3))
	if err != nil {
		return err
	}
	output, err := filepath.Abs(flag.Arg(4))
	if err != nil {
		return err
	}
	order := "staged"
	if *sdk {
		order = "sdk"
	}
	payload, err := json.Marshal([]any{"compile", source, flag.Arg(2), flag.Arg(1), output, *clean || *sdk, order})
	if err != nil {
		return err
	}
	if len(payload) > 65536 {
		return errors.New("request exceeds compiler frame size")
	}
	conn, err := net.DialTimeout("unix", flag.Arg(0), 3*time.Second)
	if err != nil {
		return err
	}
	defer conn.Close()
	if err := conn.SetDeadline(time.Now().Add(3 * time.Minute)); err != nil {
		return err
	}
	frame := binary.BigEndian.AppendUint32(nil, uint32(len(payload)))
	if _, err := conn.Write(append(frame, payload...)); err != nil {
		return err
	}
	var length uint32
	if err := binary.Read(conn, binary.BigEndian, &length); err != nil {
		return err
	}
	if length > 1<<20 {
		return errors.New("oversized compiler receipt")
	}
	response := make([]byte, length)
	if _, err := io.ReadFull(conn, response); err != nil {
		return err
	}
	var receipt struct {
		OK    json.RawMessage
		Error string
	}
	if err := json.Unmarshal(response, &receipt); err != nil {
		return err
	}
	if receipt.Error != "" {
		return errors.New(receipt.Error)
	}
	if len(receipt.OK) == 0 {
		return errors.New("missing compiler receipt")
	}
	_, err = fmt.Println(string(receipt.OK))
	return err
}

func main() {
	if err := compile(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
