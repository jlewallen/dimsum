export function ignoringKey(ev: Event) {
    const focused = window.document.activeElement;
    if (focused) {
        console.log("ignoringKey", focused.localName);
        if (focused.localName == "textarea" || focused.localName == "input") {
            return true;
        }
    }
    return false;
}
