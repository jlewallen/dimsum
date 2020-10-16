import moment from "moment";

export function getTimeStamp(): string {
    return moment()
        .utc()
        .format("YYYYMMDD_hhmmss");
}
